from pathlib import Path

APP_TITLE = "Dust & Data"

ROOT = Path(__file__).resolve().parents[2]
VOCAB_DIR = ROOT / "vocab"
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"

COHORT_SIZE = 500
COHORT_SIZES = (250, 500, 1000)
CACHE_TTL_HOURS = 24
QUEUE_PAGE_SIZE = 15
API_BASE = "https://openaccess-api.clevelandart.org/api/artworks/"

FIELDS = [
    "id",
    "accession_number",
    "title",
    "url",
    "department",
    "collection",
    "type",
    "record_type",
    "share_license_status",
    "updated_at",
    "creation_date",
    "creation_date_earliest",
    "creation_date_latest",
    "date_text",
    "creators",
    "culture",
    "technique",
    "support_materials",
    "description",
    "images",
]

# API Appendix B — exact strings
DEPARTMENTS = [
    "African Art",
    "American Painting and Sculpture",
    "Art of the Americas",
    "Chinese Art",
    "Contemporary Art",
    "Decorative Art and Design",
    "Drawings",
    "Egyptian and Ancient Near Eastern Art",
    "European Painting and Sculpture",
    "Greek and Roman Art",
    "Indian and South East Asian Art",
    "Islamic Art",
    "Japanese Art",
    "Korean Art",
    "Medieval Art",
    "Modern European Painting and Sculpture",
    "Oceania",
    "Performing Arts, Music, & Film",
    "Photography",
    "Prints",
    "Textiles",
]

# API Appendix C — exact strings (sample-mode dropdown)
TYPES = [
    "Amulets",
    "Apparatus",
    "Arms and Armor",
    "Basketry",
    "Book Binding",
    "Bound Volume",
    "Calligraphy",
    "Carpet",
    "Ceramic",
    "Coins",
    "Cosmetic Objects",
    "Drawing",
    "Embroidery",
    "Enamel",
    "Forgery",
    "Frame",
    "Funerary Equipment",
    "Furniture and woodwork",
    "Garment",
    "Glass",
    "Glyptic",
    "Illumination",
    "Implements",
    "Inlays",
    "Ivory",
    "Jade",
    "Jewelry",
    "Knitting",
    "Lace",
    "Lacquer",
    "Leather",
    "Linoleum Block",
    "Lithographic Stone",
    "Manuscript",
    "Metalwork",
    "Miniature",
    "Miscellaneous",
    "Mixed Media",
    "Monotype",
    "Mosaic",
    "Musical Instrument",
    "Netsuke",
    "Painting",
    "Papyri",
    "Photograph",
    "Plaque",
    "Plate",
    "Portfolio",
    "Portrait Miniature",
    "Print",
    "Relief",
    "Rock crystal",
    "Rubbing",
    "Sampler",
    "Scarabs",
    "Sculpture",
    "Seals",
    "Silver",
    "Spindle Whorl",
    "Stencil",
    "Stone",
    "Tapestry",
    "Textile",
    "Time-based Media",
    "Tool",
    "Velvet",
    "Vessels",
    "Wood",
    "Woodblock",
]

WEIGHTS = {
    "image": 15,
    "date": 25,
    "medium": 20,
    "attribution": 25,
    "description": 15,
}
