import os
import nltk
import re
from nltk.stem import SnowballStemmer
import pandas as pd

snowball_stemmer = SnowballStemmer("english")
verbs = ['select', 'choose', 'swipe', 'press', 'type', 'enter', 'change', 'switch', 'enable', 'open', 'import', "tell",
         "insert", "rotate", "reconnect", "start", "stop", "add", "say", 'clicking', 'disable', 'launch', 'set', 'tap',
         'click', 'go', 'turn', 'write', 'input', 'put', "cancel", "send", "map", "scroll", "create", "search",
         "interface", "tab", "initiate", "tick", "start", "exit", "close", "chose", "restart"]
stem_verbs = [snowball_stemmer.stem(w) for w in verbs]


def move_all_report():
    data_dir = r"E:\ReproduceCrashStep\ReCDroid\Artifact-Evaluation\1.worked-in-this-VM\Android-4.4.2"
    for prj in os.listdir(data_dir):
        report_path = os.path.join(data_dir, prj + "/percentresult/0/bugreport1")
        if os.path.exists(report_path):
            report_content = open(report_path, "r", encoding="UTF-8").read()
            output_file = open("../Data/RecDroid/oriReport/" + prj + ".txt", "w", encoding="UTF-8")
            output_file.write(report_content)


def get_all_report():
    report_dict = {}
    recdroid_report_dir = "../Data/RecDroid/oriReport/"
    recdroid_clean_report_dir = "../Data/RecDroid/report/"
    andror2_report_dir = "../Data/AndroR2/oriReport"
    andror2_clean_report_dir = "../Data/AndroR2/report"
    for file in os.listdir(recdroid_clean_report_dir):
        ori_report_path = os.path.join(recdroid_report_dir, file)
        clean_report_path = os.path.join(recdroid_clean_report_dir, file)
        if not (os.path.exists(clean_report_path) and os.path.exists(ori_report_path)):
            print("not find!", ori_report_path)
            print("not find!", clean_report_path)
        report_dict.setdefault(file, {"ori": ori_report_path, "clean": clean_report_path})
    for file in os.listdir(andror2_clean_report_dir):
        ori_report_path = os.path.join(andror2_report_dir, file)
        clean_report_path = os.path.join(andror2_clean_report_dir, file)
        if not (os.path.exists(clean_report_path) and os.path.exists(ori_report_path)):
            print("not find!", ori_report_path)
            print("not find!", clean_report_path)
        report_dict.setdefault(file, {"ori": ori_report_path, "clean": clean_report_path})
    return report_dict


def report_preprocess_old():
    report_dir = "../Data/RecDroid/oriReport/"
    for report_file in os.listdir(report_dir):
        report_lines = open(os.path.join(report_dir, report_file), "r", encoding="UTF-8").readlines()
        process_lines = []
        print(report_file)
        for report_line in report_lines:
            report_line = report_line.strip()
            if len(report_line) == 0:
                continue
            # print("ori report line:", report_line.strip())
            process_lines.extend(preprocess_report_line(report_line.strip()))
        print("####################################")
        print("report_lines")
        print("".join(report_lines))
        print("process_lines")
        print("\n".join(process_lines))
        print()


def report_preprocess_all():
    report_dict = get_all_report()
    for key, report_path in report_dict.items():
        print("#" * 10, key, "#" * 10)
        ori_report_lines = open(report_path["ori"], "r", encoding="UTF-8").readlines()
        ori_report_lines = [l.strip() for l in ori_report_lines if len(l.strip()) > 0]
        clean_report_lines = open(report_path["clean"], "r", encoding="UTF-8").readlines()
        clean_report_lines = [l.split("\t")[1].strip() for l in clean_report_lines if len(l.strip()) > 0]
        process_lines = []
        for report_line in ori_report_lines:
            report_line = report_line.strip()
            if len(report_line) == 0:
                continue
            process_lines.extend(preprocess_report_line(report_line.strip()))
        new_process_lines = []
        for line in process_lines:
            if line[-1] == ".":
                new_process_lines.append(line[:-1])
            else:
                new_process_lines.append(line)
        new_clean_report_lines = []
        for line in clean_report_lines:
            if line[-1] == ".":
                new_clean_report_lines.append(line[:-1])
            else:
                new_clean_report_lines.append(line)
        if "".join(new_process_lines) == "".join(new_clean_report_lines):
            print("000 same")
            print("")
        else:
            print("~~~ ori_report_lines")
            print("\n".join(ori_report_lines))
            print("~~~ process_lines")
            print("\n".join(process_lines))
            print("~~~ what i want")
            print("\n".join(clean_report_lines))
            print("")


def report_preprocess(ori_report_path, out_report_path):
    ori_report_lines = open(ori_report_path, "r", encoding="UTF-8").readlines()
    ori_report_lines = [l.strip() for l in ori_report_lines if len(l.strip()) > 0]
    process_lines = []
    only_one_line = (len(ori_report_lines) == 1)
    print(only_one_line)
    for report_line in ori_report_lines:
        report_line = report_line.strip()
        if len(report_line) == 0:
            continue
        process_lines.extend(preprocess_report_line(report_line.strip(), only_one_line))
    out_process_lines = [str(idx) + "\t" + line for idx, line in enumerate(process_lines)]
    # out_process_lines = [str(idx) + "    " + line for idx, line in enumerate(process_lines)]
    out_report_file = open(out_report_path, "w", encoding="UTF-8")
    out_report_file.write("\n".join(out_process_lines))
    out_report_file.close()
    return out_process_lines


def clean_none_verb(lines):
    has_verb_lines = []
    for line_info in lines:
        line = line_info[0]
        line_type = line_info[1]
        has_verb = False
        clean_line = re.sub("[^a-z]", " ", line.lower())
        for token in clean_line.split():
            stem_token = snowball_stemmer.stem(token)
            if stem_token in stem_verbs:
                has_verb = True
                break
        if has_verb or line_type == 1:
            has_verb_lines.append([line, line_type])
        else:
            # print("%%% no verb:", line)
            pass
    # if len(has_verb_lines) == 0 and len(lines) > 0:
    #     line0 = lines[0]
    #     has_verb_lines.append(line0)
    return has_verb_lines


def drop_useless_word(lines):
    process_lines = []
    drop_words = ["now", "also", "next", "but", "then", "\(", "than"]
    for line_info in lines:
        line = line_info[0]
        line_type = line_info[1]
        process_line = " " + line + " "
        for drop_word in drop_words:
            process_line = re.sub(r"[^a-zA-Z0-9]" + drop_word + "[^a-zA-Z0-9]", "", process_line)
            process_line = re.sub(r"[^a-zA-Z0-9]" + drop_word.capitalize() + "[^a-zA-Z0-9]", "", process_line)
        process_lines.append(process_line.strip())
    return process_lines


def clean_idx(report_line: str):
    if report_line[0] == "-":
        report_line = report_line[1:].strip()
    report_line = re.sub(r"\d\.", "", report_line).strip()
    return report_line


def preprocess_report_line(report_line: str, only_one_line: bool):
    report_line = clean_idx(report_line)
    if only_one_line:
        process_lines0 = [[report_line, 1]]
    else:
        process_lines0 = [[report_line, 0]]
    process_lines1 = split_by_token_consecutively(process_lines0)
    process_lines2 = remove_line_by_first_word(process_lines1)
    process_lines4 = split_step_token(process_lines2)
    process_lines5 = split_by_dot(process_lines4)
    process_lines6 = clean_none_verb(process_lines5)
    process_lines7 = clean_brackets(process_lines6)
    process_lines8 = drop_useless_word(process_lines7)
    process_lines9 = remove_line_by_first_word2(process_lines8)
    return process_lines9


def remove_line_by_first_word(lines):
    process_lines = []
    for line_info in lines:
        line = line_info[0]
        line_type = line_info[1]
        clean_line = re.sub("[^a-z]", " ", line.lower()).strip()
        if len(clean_line) == 0:
            continue
        first_word = snowball_stemmer.stem(clean_line.split()[0])
        # if first_word in ["install", "launch", "start", "crash", "wait", "open", "switch", "app", "don"]:
        if first_word in ["install", "launch", "crash", "wait", "switch", "app", "don"]:
            if len(line.split()) < 5 and line_type == 0:
                # print("###first_word", first_word)
                continue
            else:
                # print("###first_word not skip", line)
                pass
        process_lines.append([line, 0])
    return process_lines


def remove_line_by_first_word2(lines):
    process_lines = []
    for line in lines:
        clean_line = re.sub("[^a-z]", " ", line.lower()).strip()
        if len(clean_line) == 0:
            continue
        first_word = clean_line.split()[0]
        if first_word in ["app", "don", "you"]:
            # print("###first_word2", first_word)
            continue
        if first_word == "open" and (" app" in line or len(line.split()) < 3) and len(line.split()) < 5:
            continue
        if first_word == "start" and (" app" in line or len(line.split()) < 3) and len(line.split()) < 5:
            continue
        process_lines.append(line)
    return process_lines


def split_by_token_consecutively(lines: list):
    split_tokens = ["and ", ",", "when ", "close", "Im ", "Exception", "on Android", "from ", "& "]
    except_lists = [["andscape"], ["e.g.", "like"], ["apostroph"], ["whereyougo", "apostroph"], [], [], [], ["camera"],
                    ["oss", "privacy"]]
    input_lines = lines.copy()
    output_lines = lines.copy()
    for (split_token, except_list) in zip(split_tokens, except_lists):
        output_lines = split_by_token(input_lines, split_token, except_list)
        input_lines = output_lines.copy()
    return output_lines


def split_by_token(lines, split_token, except_list):
    split_lines = []
    for line_info in lines:
        line = line_info[0]
        line_type = line_info[1]
        split_flag = True
        for except_token in except_list:
            if except_token in line:
                split_flag = False
                break
        if split_flag and split_token in line:
            # print("$$$split by", split_token)
            for t in line.split(split_token):
                if len(t.strip()) > 0:
                    split_lines.append([t.strip(), line_type])
        else:
            split_lines.append([line, line_type])
    return split_lines


def split_by_dot(lines):
    split_token = "."
    except_list = ["e.g."]
    split_lines = []
    for line_info in lines:
        line = line_info[0]
        line_type = line_info[1]
        split_flag = True
        for except_token in except_list:
            if except_token in line:
                split_flag = False
                break
        if split_flag and split_token in line[:-1]:
            # print("$$$split by dot ", split_token)
            line = re.sub(r'([a-zA-Z])\. ', r'\1$dot$', line)
            for t in line.split("$dot$"):
                if len(t.strip()) > 0:
                    split_lines.append([t.strip(), line_type])
        else:
            split_lines.append([line, line_type])
    return split_lines


def split_step_token(lines):
    process_lines = []
    for line_info in lines:
        line = line_info[0]
        line_type = line_info[1]
        if "->" in line:
            use_brackets = re.match(".*?\((.*?->.*?)\).*?", line)
            if use_brackets:
                # print("$$$split-> use brackets", use_brackets.group(1))
                for t in use_brackets.group(1).split("->"):
                    process_lines.append([t.strip(), 1])
            else:
                # print("$$$split-> not use brackets", line)
                for t in line.split("->"):
                    process_lines.append([t.strip(), 1])
        elif "=>" in line:
            # print("$$$split=>", line)
            for t in line.split("=>"):
                process_lines.append([t.strip(), 1])
        elif ">" in line:
            # print("$$$split>", line)
            for t in line.split(">"):
                process_lines.append([t.strip(), 1])
        elif " - " in line:
            # print("$$$split-%", line)
            for t in line.split(" - "):
                process_lines.append([t.strip(), 1])
        elif " / " in line and "\\" not in line:
            # print("$$$split-%", line)
            for t in line.split(" / "):
                process_lines.append([t.strip(), 1])
        else:
            process_lines.append([line, 0])
    return process_lines


def clean_brackets(lines):
    process_lines = []
    for line_info in lines:
        line = line_info[0]
        line_type = line_info[1]
        use_brackets = re.match(".*?\(.*?\).*?", line)
        if use_brackets and "rotation" not in line:
            # print("***clean ():", line)
            clean_line = re.sub("\(.*?\)", "", line).strip()
            if len(clean_line) > 0:
                process_lines.append([clean_line, line_type])
        else:
            process_lines.append([line, line_type])
    return process_lines


def show_all_preprocess():
    res = {"name": [], "ori": [], "out": []}
    for ori_report in os.listdir("use_report"):
        ori_cont = open("use_report/" + ori_report, "r", encoding="UTF-8").read()
        out_cont = report_preprocess("use_report/" + ori_report, "temp.txt")
        out_cont = "\n".join(out_cont)
        res["name"].append(ori_report)
        res["ori"].append(ori_cont)
        res["out"].append(out_cont)
    df = pd.DataFrame(res)
    df.to_csv("test_preprocess.csv", index=False)


def gen_all_eda_report():
    res = {"prj":[]}
    for i in ["10", "20"]:
        for j in ["1", "2", "3"]:
            res.setdefault(i + "_" + j + "_ori", [])
            res.setdefault(i + "_" + j + "_res", [])
    print(res)
    eda_report_dir = "../Data/eda/eda_report/"
    all_prj = os.listdir(eda_report_dir + "10")
    all_prj.sort(key=lambda x:int(x.split(".")[0]))
    for prj in all_prj:
        res["prj"].append(prj)
        for rate in ["10", "20"]:
            for idx in ["1", "2", "3"]:
                ori_key = rate + "_" + idx + "_ori"
                res_key = rate + "_" + idx + "_res"
                report_path = eda_report_dir + rate + "/" + prj + "/" + idx + ".txt"
                ori_content = open(report_path, "r", encoding="UTF-8").read()
                proc_res = report_preprocess(report_path, "../Temp/out.txt")
                proc_res2 = "\n".join(proc_res)
                res[ori_key].append(ori_content)
                res[res_key].append(proc_res2)
    df = pd.DataFrame(res)
    df.to_csv("eda_res.csv", index=False)






if __name__ == '__main__':
    # report_preprocess_all()
    # get_all_report()
    # report_preprocess("../Data/RecDroid/oriReport/1.newsblur_s.txt", "../Temp/out.txt")
    # a = "rotation"
    # print(snowball_stemmer.stem(a))
    # a = "rotate"
    # print(snowball_stemmer.stem(a))
    # show_all_preprocess()
    # a = [["apostroph close when enter word with force", 0]]
    # print(split_by_token_consecutively(a))
    # get_all_report()
    report_preprocess("../Data/eda/eda_report/10/29.k9_2/2.txt", "../Temp/out.txt")
    # gen_all_eda_report()
