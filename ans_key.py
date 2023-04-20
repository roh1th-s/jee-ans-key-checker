from bs4 import BeautifulSoup as bs
import json
import re

def parse_responses(responseHtmlFile):
    responses_html = open(responseHtmlFile, "r")
    responses_html = responses_html.read()
    responses_bs = bs(responses_html, 'html.parser')
    e = responses_bs.find_all("div", {'class': 'section-cntnr'})
    sections = responses_bs.select("div.section-cntnr")

    section_dict = {}
    for section in sections:
        section_lbl = section.select_one("div.section-lbl")
        section_name = section_lbl.select_one("span.bold")
        section_name = str(section_name.encode_contents(), "UTF-8")
        section_name = re.sub("\n\s+", " ", section_name)
        section_dict[section_name] = []

        questions = section.select("div.question-pnl")
        for question in questions:
            menu_tbl = question.select_one("table.menu-tbl")
            t_rows = menu_tbl.select("tr")

            question_type = ''
            question_id = ''
            options = ['', '', '', '']
            chosen = None
            numerical_ans = None

            for tr in t_rows:
                tds = tr.select("td")
                label = str(tds[0].encode_contents(), 'UTF-8')
                value = str(tds[1].encode_contents(), 'UTF-8')

                if label.find("Question Type") != -1:
                    question_type = value
                elif label.find("Question ID") != -1:
                    question_id = value
                elif label.find("Option 1") != -1:
                    options[0] = value
                elif label.find("Option 2") != -1:
                    options[1] = value
                elif label.find("Option 3") != -1:
                    options[2] = value
                elif label.find("Option 4") != -1:
                    options[3] = value
                # elif label.find("Chosen") != -1:
                #     chosen = value

            if question_type == "SA":
                row_tbl = question.select_one("table.questionRowTbl")
                tds = row_tbl.select("td")
                last_td = tds[len(tds) - 1]
                numerical_ans = str(last_td.encode_contents(), "UTF-8")
                if numerical_ans.find("--") != -1:
                    numerical_ans = None

            elif question_type == "MCQ":
                tds = menu_tbl.select("td")
                last_td = tds[len(tds) - 1]
                chosen = str(last_td.encode_contents(), "UTF-8")
                if chosen.find("--") != -1:
                    chosen = None

            section_dict[section_name].append({
                'type': question_type,
                'id': question_id,
                'options': options,
                'chosen': chosen,
                'numerical_ans': numerical_ans
            })

    return section_dict

def parse_anskey(ansKeyHtmlFile):
    ans_key_html = open(ansKeyHtmlFile, "r")
    ans_key_html = ans_key_html.read()
    ans_key_bs = bs(ans_key_html, 'html.parser')

    ans_dict = {}
    trs = ans_key_bs.select("table#ctl00_LoginContent_grAnswerKey > tbody > tr")
    for tr in trs:
        if tr.attrs.get('class'):
            if tr['class'][0] == "bg-info":
                continue

        tds = tr.select("td")
        question_span = tds[1].select_one("span")
        ans_span = tds[2].select_one("span")

        question_id = str(question_span.encode_contents(), "UTF-8")
        ans = str(ans_span.encode_contents(), "UTF-8")

        ans_dict[question_id] = ans

    return ans_dict

def check_answers(responses, ansKey):
    result_dict = {}
    result_dict["report"] = {
        "Mathematics": {
            "score": 0,
            "correct": 0,
            "incorrect": 0,
            "unattempted": 0
        },
        "Physics": {
            "score": 0,
            "correct": 0,
            "incorrect": 0,
            "unattempted": 0
        },
        "Chemistry": {
            "score": 0,
            "correct": 0,
            "incorrect": 0,
            "unattempted": 0
        },
    }
    for key in responses.keys():
        sectionQuestions = responses[key]
        subjectName = key.split(" ")[0]

        result_dict[key] = []
        for question in sectionQuestions:
            question_dict = {}
            question_dict["id"] = question["id"]
            question_dict["type"] = question["type"]

            ans = ansKey[question["id"]]
            if question["type"] == "MCQ":
                chosen_as_str = question["chosen"]
                if not chosen_as_str:
                    continue

                chosen = int(chosen_as_str)
                question_dict["your choice"] = chosen
                question_dict["answer"] = question["options"].index(ans) + 1

                chosen_id = question["options"][chosen - 1]
                if chosen_id == ans:
                    result_dict["report"][subjectName]["score"] += 4
                    result_dict["report"][subjectName]["correct"] += 1
                else:
                    result_dict["report"][subjectName]["score"] -= 1
                    result_dict["report"][subjectName]["incorrect"] += 1

            elif question["type"] == "SA":
                if not question["numerical_ans"]:
                    continue

                question_dict["your answer"] = float(question["numerical_ans"])
                question_dict["answer"] = float(ans)

                if float(ans) == float(question["numerical_ans"]):
                    result_dict["report"][subjectName]["score"] += 4
                    result_dict["report"][subjectName]["correct"] += 1
                else:
                    result_dict["report"][subjectName]["score"] -= 1
                    result_dict["report"][subjectName]["incorrect"] += 1

            result_dict[key].append(question_dict)

    for subject in result_dict["report"].keys():
        correct = result_dict["report"][subject]["correct"]
        incorrect = result_dict["report"][subject]["incorrect"]
        result_dict["report"][subject]["unattempted"] = 25 - (correct + incorrect)

    return result_dict

ans_key = parse_anskey("./answerkey.html")
responses = parse_responses("./responses.html")

results = check_answers(responses, ans_key)
with open("results.json", "w") as f:
    f.write(json.dumps(results, indent=4))
