from typing import List
import dataclasses
import functools

import sqlite3


@dataclasses.dataclass
class Image:
    image_id: int
    name: str
    captions: List[str]


@dataclasses.dataclass
class Database:
    db: sqlite3.Connection

    def count_images(self) -> int:
        with self.db:
            cursor = self.db.execute(
                "SELECT COUNT(image.imageid) FROM image"
            )
            row = cursor.fetchone()
        return row[0]

    def count_captions(self) -> int:
        with self.db:
            cursor = self.db.execute(
                "SELECT COUNT(caption.captionid) FROM caption"
            )
            row = cursor.fetchone()
        return row[0]

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
        
    def get_least_images(self) -> List[Image]:
        with self.db:
            cursor = self.db.execute(
                """
                SELECT image.*
                FROM image 
                LEFT JOIN caption ON image.imageid = caption.captionimage 
                GROUP BY image.imageid
                ORDER BY COUNT(caption.captionid) ASC 
                LIMIT 10
                """
            )
            rows = cursor.fetchall()

        return [
            Image(
                image_id=row['imageid'],
                name=row['imagename'],
                captions=self.get_captions(row['imageid']),
            )
            for row in rows
        ]
    
    def get_all_images(self) -> List[Image]:
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

    
    def get_captions(self, image_id: int) -> List[str]:
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