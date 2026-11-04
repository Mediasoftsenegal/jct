from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Caisse

# --------------------------------------------------------------------------- #
#  Tri des tableaux factures / encaissements (clic sur l'en-tete de colonne,
#  decroissant par defaut).
# --------------------------------------------------------------------------- #
CHAMPS_TRI_FACTURES = {"numero", "client", "montant", "reliquat"}
CHAMPS_TRI_PAIEMENTS = {"facture", "type", "mode", "montant"}


def _cle_tri_facture(f, champ):
    return {
        "numero": f.numero or "",
        "client": f.client.nom if f.client_id else "",
        "montant": f.montant_total,
        "reliquat": f.reliquat,
    }[champ]


def _cle_tri_paiement(p, champ):
    return {
        "facture": p.facture.numero if p.facture_id else "",
        "type": p.get_type_paiement_display(),
        "mode": p.get_mode_display(),
        "montant": p.montant,
    }[champ]


def _trier(request, items, prefixe, champs_valides, cle):
    """Trie `items` (liste ou queryset) selon les parametres GET
    `tri_<prefixe>` / `dir_<prefixe>`. Decroissant par montant par defaut."""
    champ = request.GET.get(f"tri_{prefixe}", "montant")
    if champ not in champs_valides:
        champ = "montant"
    decroissant = request.GET.get(f"dir_{prefixe}") != "asc"
    items = sorted(items, key=lambda i: cle(i, champ), reverse=decroissant)
    return items, champ, "desc" if decroissant else "asc"


def _contexte_tableaux(request, jour, caisse_obj=None):
    """Factures et paiements du jour, tries, prets pour le template."""
    from ventes.models import Facture, Paiement

    factures = list(
        Facture.objects.filter(date__date=jour, annulee=False).select_related("client")
    )
    paiements = list(Paiement.objects.filter(date__date=jour).select_related("facture"))

    factures, tri_f, dir_f = _trier(request, factures, "f", CHAMPS_TRI_FACTURES, _cle_tri_facture)
    paiements, tri_p, dir_p = _trier(request, paiements, "p", CHAMPS_TRI_PAIEMENTS, _cle_tri_paiement)

    return {
        "factures": factures,
        "paiements": paiements,
        "tri_f": tri_f, "dir_f": dir_f,
        "tri_p": tri_p, "dir_p": dir_p,
    }


@login_required
def liste(request):
    caisses = Caisse.objects.order_by("-date")[:60]
    today = timezone.localdate()
    caisse_jour = Caisse.objects.filter(date=today).first()
    contexte = {
        "actif": "caisse",
        "caisses": caisses,
        "today": today,
        "caisse_jour": caisse_jour,
    }
    return render(request, "caisse/liste.html", contexte)


@login_required
def voir(request):
    """Consulte la caisse d'une date choisie : affiche la cloture existante
    si elle existe, sinon un calcul en temps reel (non enregistre)."""
    date_str = request.GET.get("date", "").strip()
    if date_str:
        try:
            jour = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Date invalide.")
            return redirect("caisse:liste")
    else:
        jour = timezone.localdate()

    caisse = Caisse.objects.filter(date=jour).first()
    if not caisse:
        caisse = Caisse(**Caisse.calculer(jour))

    contexte = {
        "actif": "caisse",
        "caisse": caisse,
        "peut_cloturer": request.user.has_perm("caisse.peut_cloturer_caisse"),
        **_contexte_tableaux(request, jour),
    }
    return render(request, "caisse/detail.html", contexte)


@login_required
@permission_required("caisse.peut_cloturer_caisse", raise_exception=True)
@require_POST
def cloturer(request):
    date_str = request.POST.get("date", "").strip()
    if date_str:
        try:
            jour = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Date invalide.")
            return redirect("caisse:liste")
    else:
        jour = timezone.localdate()

    caisse = Caisse.cloturer(date=jour, user=request.user)
    messages.success(
        request,
        f"Caisse du {jour:%d/%m/%Y} clôturée : "
        f"encaissé {caisse.total_encaisse:.0f}, reliquat jour {caisse.total_non_paye:.0f}.",
    )
    return redirect("caisse:detail", pk=caisse.pk)


@login_required
def detail(request, pk):
    caisse = get_object_or_404(Caisse, pk=pk)
    contexte = {
        "actif": "caisse",
        "caisse": caisse,
        "peut_cloturer": request.user.has_perm("caisse.peut_cloturer_caisse"),
        **_contexte_tableaux(request, caisse.date),
    }
    return render(request, "caisse/detail.html", contexte)
