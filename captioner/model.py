import dataclasses
import functools

import sqlite3


@dataclasses.dataclass
class Image:
    image_id: int
    name: str
    captions: list[str]


@dataclasses.dataclass
class Database:
    db: sqlite3.Connection

    def get_image(self, image_id: int) -> Image:
        with self.db:
            cursor = self.db.execute(
                "SELECT * FROM image WHERE imageid = ?",
                (image_id,),
            )
            row = cursor.fetchone()

        if row is None:
            raise LookupError("no image with that id")
        else:
            return Image(
                image_id=image_id,
                name=row["imagename"],
                captions=self.get_captions(image_id),
            )
        
    def get_least_image(self) -> Image:
        with self.db:
            cursor = self.db.execute(
                """
                SELECT image.*
                FROM image 
                LEFT JOIN caption ON image.imageid = caption.captionimage 
                GROUP BY image.imageid
                ORDER BY COUNT(caption.captionid) ASC 
                LIMIT 1
                """
            )
            row = cursor.fetchone()
        

        if row is None:
            raise LookupError("no images!")
        else:
            return Image(
                image_id=row['imageid'],
                name=row['imagename'],
                captions=self.get_captions(row['imageid']),
            )
    
    def get_all_images(self) -> list[Image]:
        # warning! this is the whole database!
        with self.db:
            cursor = self.db.execute("SELECT * FROM image")
            rows = cursor.fetchall()

        return [
            Image(
                image_id=row['imageid'],
                name=row["imagename"],
                captions=self.get_captions(row['imageid']),
            )
            for row in rows
        ]

    
    def get_captions(self, image_id: int) -> list[str]:
        with self.db:
            cursor = self.db.execute(
                "SELECT * FROM caption WHERE captionimage = ?",
                (image_id,),
            )
            rows = cursor.fetchall()

        return [row["captiontext"] for row in rows]

    def add_caption(self, image_id: int, caption: str) -> None:
        # this throws lookuperror if no such image exists
        self.get_image(image_id)
        
        with self.db:
            self.db.execute(
                "INSERT INTO caption (captionimage, captiontext) VALUES (?,?)",
                (image_id, caption),
            )