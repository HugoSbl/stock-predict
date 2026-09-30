"""Référentiels : pays, catégories, fournisseurs, entrepôts, produits."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Pays:
    code_pays: str
    nom_pays: str
    taux_tva: float
    devise: str


@dataclass(frozen=True)
class Categorie:
    id_categorie: int
    libelle_categorie: str
    amplitude_saison: float  # variation annuelle relative (0,3 = ±30 %)
    jour_pic: int  # jour de l'année du pic saisonnier
    effet_noel: float  # multiplicateur du 15 au 24 décembre
    effet_paques: float  # multiplicateur la semaine avant Pâques
    effet_vacances: float  # multiplicateur pendant les vacances scolaires
    prix_min: float
    prix_max: float


@dataclass(frozen=True)
class Fournisseur:
    id_fournisseur: int
    code_fournisseur: str
    nom_fournisseur: str
    pays_fournisseur: str
    delai_moyen_jours: int


@dataclass(frozen=True)
class Entrepot:
    id_entrepot: int
    code_entrepot: str
    nom_entrepot: str
    ville: str
    capacite_max: int
    code_pays: str
    taille: float  # multiplicateur de volume


@dataclass(frozen=True)
class Produit:
    id_produit: int
    reference: str
    libelle: str
    prix_unitaire_ht: float
    seuil_alerte: int
    id_categorie: int
    id_fournisseur_habituel: int


PAYS = [
    Pays("FR", "France", 20.0, "EUR"),
    Pays("DE", "Allemagne", 19.0, "EUR"),
]

CATEGORIES = [
    Categorie(1, "Épicerie salée", 0.08, 15, 1.10, 1.00, 0.97, 0.8, 4.5),
    Categorie(2, "Épicerie sucrée", 0.10, 340, 1.80, 1.45, 1.00, 1.0, 6.0),
    Categorie(3, "Boissons", 0.35, 196, 1.30, 1.10, 1.10, 0.5, 5.0),
    Categorie(4, "Produits laitiers", 0.05, 30, 1.15, 1.05, 0.97, 0.6, 4.0),
    Categorie(5, "Surgelés", 0.30, 200, 1.20, 1.00, 1.05, 1.5, 8.0),
    Categorie(6, "Hygiène & beauté", 0.05, 180, 1.05, 1.00, 1.00, 1.2, 9.0),
    Categorie(7, "Entretien", 0.12, 100, 1.00, 1.05, 0.95, 1.0, 7.0),
    Categorie(8, "Snacking & apéritif", 0.20, 170, 1.35, 1.10, 1.12, 0.9, 4.5),
]

FOURNISSEURS = [
    Fournisseur(1, "F-LACTA", "Lactalis Distribution", "France", 4),
    Fournisseur(2, "F-DANO", "Danone Supply", "France", 5),
    Fournisseur(3, "F-NESTL", "Nestlé Europe", "Suisse", 9),
    Fournisseur(4, "F-BARIL", "Barilla Logistica", "Italie", 12),
    Fournisseur(5, "F-EBRO", "Ebro Foods", "Espagne", 10),
    Fournisseur(6, "F-OETK", "Dr. Oetker", "Allemagne", 6),
    Fournisseur(7, "F-HENK", "Henkel Consumer", "Allemagne", 7),
    Fournisseur(8, "F-UNIL", "Unilever Europe", "Pays-Bas", 8),
    Fournisseur(9, "F-COCA", "Coca-Cola Europacific", "Belgique", 5),
    Fournisseur(10, "F-LUTT", "Lutti Confiserie", "France", 14),
    Fournisseur(11, "F-PICA", "Picard Surgelés", "France", 6),
    Fournisseur(12, "F-LESI", "Lesieur", "France", 7),
]

# Fournisseurs possibles par catégorie
FOURNISSEURS_PAR_CATEGORIE = {
    1: [4, 5, 12, 3],
    2: [3, 10, 6],
    3: [9, 2, 3],
    4: [1, 2],
    5: [11, 6],
    6: [8, 7],
    7: [7, 8],
    8: [3, 6, 10],
}

ENTREPOTS = [
    Entrepot(1, "FR-LYS", "Lyon-Sud", "Lyon", 900_000, "FR", 1.00),
    Entrepot(2, "FR-PAN", "Paris-Nord", "Paris", 1_200_000, "FR", 1.30),
    Entrepot(3, "FR-LIE", "Lille-Est", "Lille", 700_000, "FR", 0.80),
    Entrepot(4, "DE-BEW", "Berlin-Ouest", "Berlin", 1_000_000, "DE", 1.20),
    Entrepot(5, "DE-MUE", "Munich-Est", "Munich", 850_000, "DE", 1.00),
    Entrepot(6, "DE-HAN", "Hambourg-Nord", "Hambourg", 750_000, "DE", 0.90),
]

# Produits des maquettes et parcours du dossier : références imposées
PRODUITS_MAQUETTES = [
    ("REF-4512", "Lait UHT demi-écrémé 1L", 4),
    ("REF-8830", "Pâtes coquillettes 500g", 1),
    ("REF-1204", "Eau minérale 6x1,5L", 3),
    ("REF-3391", "Café moulu 250g", 2),
    ("REF-7702", "Riz basmati 1kg", 1),
    ("REF-5518", "Jus d'orange 1L", 3),
    ("REF-9915", "Huile de tournesol 1L", 1),
    ("REF-2087", "Sucre en poudre 1kg", 2),
]

ARTICLES = {
    1: [
        "Pâtes spaghetti",
        "Pâtes penne",
        "Riz long grain",
        "Lentilles vertes",
        "Couscous moyen",
        "Sauce tomate basilic",
        "Thon au naturel",
        "Soupe de légumes",
        "Farine de blé T55",
        "Pois chiches",
        "Maïs doux",
        "Huile d'olive vierge extra",
        "Vinaigre de vin",
        "Moutarde de Dijon",
        "Sel de Guérande",
    ],
    2: [
        "Chocolat noir 70%",
        "Chocolat au lait",
        "Biscuits petit-beurre",
        "Confiture de fraises",
        "Pâte à tartiner",
        "Céréales au chocolat",
        "Madeleines",
        "Miel de fleurs",
        "Compote de pommes",
        "Bonbons gélifiés",
        "Cookies aux pépites",
        "Muesli croustillant",
    ],
    3: [
        "Eau gazeuse",
        "Soda cola",
        "Limonade",
        "Jus de pomme",
        "Thé glacé pêche",
        "Sirop de menthe",
        "Nectar multifruits",
        "Boisson énergisante",
        "Eau aromatisée citron",
        "Jus de raisin",
    ],
    4: [
        "Yaourt nature",
        "Beurre doux",
        "Crème fraîche épaisse",
        "Emmental râpé",
        "Lait entier",
        "Fromage blanc",
        "Camembert",
        "Yaourt aux fruits",
        "Crème dessert vanille",
        "Comté affiné",
    ],
    5: [
        "Glace vanille",
        "Pizza margherita",
        "Légumes pour poêlée",
        "Frites allégées",
        "Poisson pané",
        "Bâtonnets glacés",
        "Épinards hachés",
        "Sorbet citron",
        "Croissants à cuire",
        "Haricots verts extra-fins",
    ],
    6: [
        "Gel douche",
        "Shampooing",
        "Dentifrice menthe",
        "Déodorant",
        "Crème solaire SPF50",
        "Savon liquide",
        "Coton-tiges",
        "Mouchoirs",
    ],
    7: [
        "Liquide vaisselle",
        "Lessive liquide",
        "Nettoyant multi-surfaces",
        "Éponges",
        "Sacs poubelle 50L",
        "Pastilles lave-vaisselle",
        "Papier toilette",
        "Essuie-tout",
        "Adoucissant",
    ],
    8: [
        "Chips nature",
        "Cacahuètes grillées",
        "Crackers apéritif",
        "Biscuits salés",
        "Olives vertes",
        "Tortillas chips",
        "Barres céréales",
        "Pistaches",
        "Mélange apéritif",
    ],
}

MARQUES = ["", " — marque distributeur", " — premier prix", " — bio", " — format familial"]
FORMATS = {
    1: ["500g", "1kg", "400g"],
    2: ["200g", "400g", "1kg"],
    3: ["1L", "1,5L", "6x1,5L", "33cl x6"],
    4: ["500g", "1L", "4x125g", "250g"],
    5: ["450g", "1kg", "750g"],
    6: ["250ml", "400ml", "75ml"],
    7: ["1L", "x10", "2L"],
    8: ["150g", "300g", "200g"],
}


def generer_produits(rng: np.random.Generator, nb_produits: int) -> list[Produit]:
    """Catalogue déterministe : les produits des maquettes, puis des articles génériques."""
    references_prises = {ref for ref, _, _ in PRODUITS_MAQUETTES}
    candidats: list[tuple[str, int]] = [(libelle, cat) for _, libelle, cat in PRODUITS_MAQUETTES]
    vus = {libelle for libelle, _ in candidats}
    while len(candidats) < nb_produits:
        cat = int(rng.integers(1, len(CATEGORIES) + 1))
        article = ARTICLES[cat][int(rng.integers(len(ARTICLES[cat])))]
        fmt = FORMATS[cat][int(rng.integers(len(FORMATS[cat])))]
        libelle = f"{article} {fmt}{MARQUES[int(rng.integers(len(MARQUES)))]}"
        if libelle not in vus:
            vus.add(libelle)
            candidats.append((libelle, cat))

    produits = []
    refs_maquettes = [ref for ref, _, _ in PRODUITS_MAQUETTES]
    for i, (libelle, cat) in enumerate(candidats):
        if i < len(refs_maquettes):
            reference = refs_maquettes[i]
        else:
            while True:
                reference = f"REF-{int(rng.integers(1000, 10000))}"
                if reference not in references_prises:
                    references_prises.add(reference)
                    break
        categorie = CATEGORIES[cat - 1]
        prix = round(float(rng.uniform(categorie.prix_min, categorie.prix_max)), 2)
        fournisseurs = FOURNISSEURS_PAR_CATEGORIE[cat]
        produits.append(
            Produit(
                id_produit=i + 1,
                reference=reference,
                libelle=libelle,
                prix_unitaire_ht=prix,
                seuil_alerte=0,  # calculé après simulation de la demande (monde.py)
                id_categorie=cat,
                id_fournisseur_habituel=fournisseurs[int(rng.integers(len(fournisseurs)))],
            )
        )
    return produits
