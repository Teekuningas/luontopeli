import os
import requests
import json
import random

from datetime import timedelta

from flask import Flask
from flask import session
from flask import render_template
from flask import url_for
from flask import redirect
from flask import request
from flask import flash


app = Flask(__name__)
app.secret_key = os.environ.get("LUONTOPELI_APP_KEY", "SECRET")
app.permanent_session_lifetime = timedelta(days=3650)


@app.before_request
def make_session_permanent():
    session.permanent = True


api_url = "https://api.laji.fi/v0"
api_token = os.environ.get("LUONTOPELI_API_TOKEN", "")

n_images = 5

quiz_types = {
    "plant_easy": {
        "amount": 10,
        "depth": 20,
        "group_filter": "MVL.343",
        "text": "Helpot kasvit",
    },
    "plant_hard": {
        "amount": 20,
        "depth": 50,
        "group_filter": "MVL.343",
        "text": "Vaikeat kasvit",
    },
    "mushroom_easy": {
        "amount": 10,
        "depth": 20,
        "group_filter": "MVL.24",
        "text": "Helpot sienet",
    },
    "mushroom_hard": {
        "amount": 20,
        "depth": 50,
        "group_filter": "MVL.24",
        "text": "Vaikeat sienet",
    },
    "bird_easy": {
        "amount": 10,
        "depth": 20,
        "group_filter": "MVL.1",
        "text": "Helpot linnut",
    },
    "bird_hard": {
        "amount": 20,
        "depth": 50,
        "group_filter": "MVL.1",
        "text": "Vaikeat linnut",
    },
}


def get_question(quiz, key=None, reset_cache=False):
    """queries all taxa, samples species for question, and gets image"""
    result = requests.get(api_url)

    # species are filtered based on their informal group and observation count
    group_filter = quiz["group_filter"]
    depth = quiz["depth"]

    if reset_cache:
        payload = {
            "species": True,
            "lang": "fi",
            "informalGroupFilters": group_filter,
            "hasMediaFilter": True,
            "onlyFinnish": True,
            "pageSize": 5000,
            "access_token": api_token,
        }
        response = requests.get("/".join([api_url, "taxa"]), params=payload)
        taxonomy = json.loads(response.content)

        print("Total: " + str(taxonomy["total"]))

        data = []
        for species in taxonomy["results"]:
            try:
                species_id = species["id"]
                species_name = species["vernacularName"]
                observation_count = species["observationCount"]
                data.append((species_id, species_name, observation_count))
            except Exception as exc:
                pass

        data = sorted(data, key=lambda x: x[2], reverse=True)[:depth]
    else:
        data = session["question_cache"]

    if key:
        idx = [idx for idx in range(len(data)) if data[idx][0] == key][0]
        picked = [data[idx]]
        picked.extend(random.sample(data[:idx] + data[idx + 1 :], 3))
    else:
        # dont allow same question to come twice
        while True:
            picked = random.sample(data, 4)
            if picked[0][0] not in session["past_questions"]:
                session["past_questions"].append(picked[0][0])
                break

    species_id = picked[0][0]
    species_name = picked[0][1]

    options = [val[1].capitalize() for val in picked]
    random.shuffle(options)

    answer = species_name.capitalize()

    payload = {
        "lang": "fi",
        "access_token": api_token,
    }
    response = requests.get(
        "/".join([api_url, "taxa", species_id, "media"]), params=payload
    )
    content = json.loads(response.content)

    tryouts = 10
    urls = []
    already = []
    for idx in range(tryouts):
        media = random.sample(content, 1)[0]
        if media["fullURL"] not in already:
            url = {"url": media["fullURL"], "author": media.get("copyrightOwner", "")}
            urls.append(url)
            already.append(media["fullURL"])

    urls = urls[:n_images]

    question = {
        "answer": answer,
        "question_urls": urls,
        "options": options,
    }

    return species_id, question, data


def create_info():
    info = {}
    for key in quiz_types:
        info[key] = {}
        info[key]["ncorrect"] = session.get(key + "_ncorrect", 0)
        info[key]["text"] = quiz_types[key]["text"]
        info[key]["ntotal"] = quiz_types[key]["amount"]
    return info


@app.route("/reset", methods=["GET"])
def reset():
    for quiz_type in quiz_types:
        session[quiz_type + "_ncorrect"] = 0
    return redirect(url_for("index"))


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", info=create_info())


@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    # this should happen when starting a quiz.
    # reset most of the session
    if "type" in request.args:
        quiz_type = request.args.get("type")
        session["quiz_type"] = quiz_type
        session["ncorrect"] = 0
        session["current_question"] = 1
        session["past_questions"] = []

        species_id, _, all_species = get_question(
            quiz_types[quiz_type], key=None, reset_cache=True
        )
        session["current_question_key"] = species_id
        session["question_cache"] = all_species

        return redirect(url_for("quiz"))

    # check that session is fine
    current_question = session.get("current_question")
    if not current_question:
        return redirect(url_for("index"))

    quiz_type = session.get("quiz_type")
    if not quiz_type:
        return redirect(url_for("index"))

    ntotal = quiz_types.get(quiz_type, {}).get("amount")
    if not ntotal:
        return redirect(url_for("index"))

    question_key = session.get("current_question_key")
    if not question_key:
        return redirect(url_for("index"))

    question_data = get_question(quiz_types[quiz_type], question_key)[1]
    if not question_data:
        return redirect(url_for("index"))

    correct_answer = question_data["answer"]

    if "ncorrect" not in session:
        return redirect(url_for("index"))

    # happens when answer is submitted
    if request.method == "POST":
        answer = request.form.get("answer")
        if not answer:
            return redirect(url_for("index"))

        if answer == correct_answer:
            session["ncorrect"] += 1

        # set the current question to the next number when checked
        session["current_question"] += 1
        session["current_question_key"] = get_question(quiz_types[quiz_type])[0]

        if current_question >= ntotal:
            # update sticky correct counts
            sticky_ncorrect = session.get(quiz_type + "_ncorrect")
            if not sticky_ncorrect or sticky_ncorrect < session["ncorrect"]:
                session[quiz_type + "_ncorrect"] = session["ncorrect"]

            return render_template(
                "summary.html",
                ncorrect=session["ncorrect"],
                ntotal=quiz_types[quiz_type]["amount"],
            )
        else:
            return redirect(url_for("quiz"))

    # GET request, happens when a question is rendered.
    # every submit leads to two requests, one POST and one GET

    if current_question > ntotal:
        return render_template(
            "summary.html",
            ncorrect=session["ncorrect"],
            ntotal=quiz_types[quiz_type]["amount"],
        )

    question_urls = question_data["question_urls"]
    options = question_data["options"]
    return render_template(
        "quiz.html",
        ncurrent=current_question,
        ntotal=quiz_types[quiz_type]["amount"],
        question_urls=question_urls,
        correct_answer=correct_answer,
        options=options,
    )


def main():
    app.run()


if __name__ == "__main__":
    main()
