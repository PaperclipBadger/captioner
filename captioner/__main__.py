from typing import Optional

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

def get_next_image(database) -> Optional[model.Image]:
    global request_count

    next_images = database.get_least_images()
    i = next(request_count)
    return (
        next_images[i % len(next_images)]
        if next_images else None
    )


@app.route("/")
def home():
    database = model.Database(get_db())
    return flask.render_template(
        "home.html",
        image_count=database.count_images(),
        caption_count=database.count_captions(),
        next_image=get_next_image(database),
    )
    
@app.route("/<int:image_id>")
def caption(image_id: int):
    database = model.Database(get_db())
    image = database.get_image(image_id)
    return flask.render_template(
        "caption.html",
        image=image,
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
    database = model.Database(get_db())
    image_id = int(flask.request.form["image_id"])
    caption_text = flask.request.form["caption_text"]
    database.add_caption(image_id, caption_text)

    next_image = get_next_image(database)
    return flask.redirect(f"/{next_image.image_id}")


if __name__ == "__main__":
    app.run(debug=True)