"""JSON-friendly intermediate document representation (IR)."""
from dataclasses import dataclass, asdict, field


@dataclass
class Block:
    kind: str  # title|heading|paragraph|list|quote|equation|image|table|footnote
    text: str = ""
    level: int = 0
    bbox: list[float] = field(default_factory=list)
    size: float = 0.0
    image: str = ""  # relative assets/path, never absolute
    rows: list[list[str]] = field(default_factory=list)
    translation: str = ""
    latex: str = ""  # Only when OCR successfully returns latex
    equation_crop: str = ""  # PNG source for review when OCR enabled
    vector_svg: str = ""  # optional original vector asset; Markdown uses PNG
    table_pages: list[int] = field(default_factory=list)
    spans: list[list[int]] = field(default_factory=list)  # optional [row,col,rowspan,colspan]
    review: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value):
        fields = cls.__dataclass_fields__
        return cls(**{k: v for k, v in value.items() if k in fields})

    def as_dict(self):
        return asdict(self)


@dataclass
class Page:
    number: int
    width: float
    height: float
    blocks: list[Block]

    @classmethod
    def from_dict(cls, value):
        return cls(value["number"], value["width"], value["height"],
                   [Block.from_dict(b) for b in value["blocks"]])

    def as_dict(self):
        return asdict(self)
