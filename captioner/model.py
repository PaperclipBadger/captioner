from typing import List, Mapping
import collections
import dataclasses
import functools
import inspect
import math

import sqlite3


@dataclasses.dataclass
class Image:
    image_id: int
    name: str
    captions: List[str]


def cached(wrapped):
    sig = inspect.signature(wrapped)

    @functools.wraps(wrapped)
    def method(self, *args, **kwargs):
        binding = sig.bind_partial(*args, **kwargs)
        cache_key = (method.__name__, *binding.arguments.values())

        try:
            return self.cache[cache_key]
        except KeyError:
            self.cache[cache_key] = wrapped(self, *args, **kwargs)
            return self.cache[cache_key]
        
    return method


def word_cloud(corpus: List[str]) -> Mapping[str, float]:
    counts = collections.Counter(
        word.casefold().strip(",.!?'\"")
        for sentence in corpus
        for word in sentence.split()
    )
    denominator = max(counts.values())
    words = sorted(counts.keys())
    return {word: math.sqrt(counts[word] / denominator) for word in words}


@dataclasses.dataclass
class Database:
    db: sqlite3.Connection
    cache: dict = dataclasses.field(default_factory=dict)

    @cached
    def count_images(self) -> int:
        with self.db:
            cursor = self.db.execute(
                "SELECT COUNT(image.imageid) FROM image"
            )
            row = cursor.fetchone()
        return row[0]

    @cached
    def count_captions(self) -> int:
        with self.db:
            cursor = self.db.execute(
                "SELECT COUNT(caption.captionid) FROM caption"
            )
            row = cursor.fetchone()
        return row[0]

    @cached
    def word_cloud(self) -> Mapping[str, float]:
        with self.db:
            cursor = self.db.execute("SELECT * FROM caption")
            rows = cursor.fetchall()
        
        corpus = [row["captiontext"] for row in rows]
        return word_cloud(corpus) 

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
                captions=self.get_captions_for_image(image_id),
            )
        
    @cached
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
                captions=self.get_captions_for_image(row['imageid']),
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
                captions=self.get_captions_for_image(row['imageid']),
            )
            for row in rows
        ]

    def get_captions_for_image(self, image_id: int) -> List[str]:
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
        
        # clear the cache on changes
        self.cache.clear()