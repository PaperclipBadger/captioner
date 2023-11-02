from typing import Optional, Mapping

import collections
import csv
import io
import itertools
import sqlite3

import flask

from captioner import model


app = flask.Flask(__name__)


def get_db():
    if 'db' not in flask.g:
        flask.g.db = sqlite3.connect(
            "images.db",
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        flask.g.db.row_factory = sqlite3.Row

    return flask.g.db


@app.teardown_appcontext
def close_db(exception=None):
    try:
        db = flask.g.pop('db')
    except KeyError:
        pass
    else:
        db.close()


request_count = iter(itertools.count())

def get_next_image(database: model.Database) -> Optional[model.Image]:
    global request_count

    next_images = database.get_caption_counts()
    i = next(request_count) % min(len(next_images), 10)
    return (
        next(itertools.islice(next_images, i, i + 1))
        if next_images else None
    )

def progress_bar(database: model.Database) -> Mapping[int, float]:
    counts = database.get_caption_counts()
    count_counts = collections.Counter(counts.values())
    return {
        i: count_counts[i] / len(counts)
        for i in range(max(count_counts), -1, -1)
    }


@app.route("/")
def home():
    database = model.Database(get_db())
    return flask.render_template(
        "home.html",
        image_count=database.count_images(),
        caption_count=database.count_captions(),
        progress_bar=progress_bar(database),
        next_image=get_next_image(database),
        word_cloud=database.word_cloud(),
    )
    
@app.route("/<int:image_id>")
def caption(image_id: int):
    database = model.Database(get_db())
    image = database.get_image(image_id)
    return flask.render_template(
        "caption.html",
        image=image,
        error=flask.request.args.get("error", None),
    )

@app.route("/download")
def download():
    database = model.Database(get_db())
    images = database.get_all_images()

    csv_rows = [
        [image.image_id, image.name, caption]
        for image in images
        for caption in image.captions
    ]

    file = io.StringIO()
    cw = csv.writer(file)
    cw.writerows(csv_rows)
    output = flask.make_response(file.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=captions.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route("/api/caption", methods=["POST"])
def api_add_caption():
    image_id = int(flask.request.form["image_id"])
    caption_text = flask.request.form["caption_text"].strip()

    if not caption_text:
        return flask.redirect(flask.url_for("caption", image_id=image_id, error="No caption text provided"))
    else:
        database = model.Database(get_db())
        database.add_caption(image_id, caption_text)
        next_image = get_next_image(database)
        return flask.redirect(flask.url_for("caption", image_id=next_image))


if __name__ == "__main__":
    app.run(debug=True)