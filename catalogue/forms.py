from django import forms

from stock.models import Fournisseur

from .models import TypeArticle, categorie_article


class ModificationGroupeeForm(forms.Form):
    """Champs appliqués à tous les articles sélectionnés ; un champ vide ne modifie pas l'article."""

    categorie_articles = forms.ModelChoiceField(
        label="Catégorie", queryset=categorie_article.objects.all(), required=False,
        empty_label="— ne pas modifier —",
    )
    type_article = forms.ModelChoiceField(
        label="Type", queryset=TypeArticle.objects.all(), required=False,
        empty_label="— ne pas modifier —",
    )
    fournisseur = forms.ModelChoiceField(
        label="Fournisseur", queryset=Fournisseur.objects.all(), required=False,
        empty_label="— ne pas modifier —",
    )
    prix_achat_liquide = forms.DecimalField(
        label="Prix d'achat (liquide)", max_digits=12, decimal_places=2, min_value=0, required=False,
    )
    prix_achat_emballage = forms.DecimalField(
        label="Prix d'achat (emballage)", max_digits=12, decimal_places=2, min_value=0, required=False,
    )
    prix_bouteille = forms.DecimalField(
        label="Prix de vente par bouteille", max_digits=12, decimal_places=2, min_value=0, required=False,
    )

    def champs_a_modifier(self):
        return {nom: valeur for nom, valeur in self.cleaned_data.items() if valeur not in (None, "")}
