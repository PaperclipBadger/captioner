import sqlite3
import pathlib

HERE = pathlib.Path(__file__).parent
IMAGE_DIR = HERE / 'static' / 'images'
SCRIPT = """
DROP TABLE IF EXISTS image;
DROP TABLE IF EXISTS caption;

CREATE TABLE image (
  imageid INTEGER PRIMARY KEY AUTOINCREMENT,
  imagename TEXT UNIQUE NOT NULL
);

CREATE TABLE caption (
  captionid INTEGER PRIMARY KEY AUTOINCREMENT,
  captionimage INTEGER NOT NULL,
  captiontext TEXT NOT NULL,
  FOREIGN KEY (captionimage) REFERENCES image(imageid)
);
"""

db = sqlite3.connect(
    "images.db",
    detect_types=sqlite3.PARSE_DECLTYPES,
)
db.executescript(SCRIPT)

for image in IMAGE_DIR.iterdir():
    with db:
        db.execute(
            "INSERT INTO image (imagename) VALUES (?)",
            (image.name,),
        )