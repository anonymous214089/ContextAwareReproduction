import json
import os
import re


def get_recdroid_apk_info_old():
    rec_droidbot_dir = "../Data/RecDroid/DroidBotRes/"
    recdroid_apk_info = {}
    for prj_dir in os.listdir(rec_droidbot_dir):
        if "_new" in prj_dir or "_old" in prj_dir:
            continue
        prj_idx = int(prj_dir.split(".")[0])
        prj_utg_js = open(rec_droidbot_dir + prj_dir + "/utg.js", "r").readlines()
        prj_utg_json = "".join(prj_utg_js[1:])
        prj_utg_json = json.loads(prj_utg_json)
        main_activity_node = prj_utg_json["nodes"][1]
        pkg_name = main_activity_node["package"]
        act_name = main_activity_node["activity"]
        recdroid_apk_info.setdefault(prj_idx, {"appPackage": pkg_name, "appActivity": act_name})
    # for k, v in recdroid_apk_info.items():
    #     print(k, v)
    return recdroid_apk_info


def get_andror2_apk_info_old():
    rec_droidbot_dir = "../Data/AndroR2/DroidBotRes/"
    recdroid_apk_info = {}
    for prj_dir in os.listdir(rec_droidbot_dir):
        if "_new" in prj_dir or "_old" in prj_dir:
            continue
        prj_idx = int(prj_dir.split(".")[0])
        if not os.path.exists(rec_droidbot_dir + prj_dir + "/utg.js"):
            continue
        prj_utg_js = open(rec_droidbot_dir + prj_dir + "/utg.js", "r").readlines()
        prj_utg_json = "".join(prj_utg_js[1:])
        prj_utg_json = json.loads(prj_utg_json)
        main_activity_node = prj_utg_json["nodes"][1]
        pkg_name = main_activity_node["package"]
        act_name = main_activity_node["activity"]
        recdroid_apk_info.setdefault(prj_idx, {"appPackage": pkg_name, "appActivity": act_name})
    # for k, v in recdroid_apk_info.items():
    #     print(k, v)
    return recdroid_apk_info


def get_andror2_apk_info():
    ori_apk_info = json.load(open("../Data/AndroR2/activity.txt", "r"))
    apk_info = {}
    for apk_name, info in ori_apk_info.items():
        apk_info.setdefault(int(apk_name.split(".")[0]),
                            {"appPackage": info["appPackage"], "appActivity": info["appActivity"][0]})
    return apk_info


def get_mydata_apk_info():
    ori_apk_info = json.load(open("../Data/MyData/activity.txt", "r"))
    apk_info = {}
    for apk_name, info in ori_apk_info.items():
        apk_info.setdefault(int(apk_name.split("_")[0]),
                            {"appPackage": info["appPackage"], "appActivity": info["appActivity"][0]})
    return apk_info


def get_recdroid2_apk_info():
    ori_apk_info = json.load(open("../Data/RecDroid2/activity.txt", "r"))
    apk_info = {}
    for apk_name, info in ori_apk_info.items():
        apk_info.setdefault(int(apk_name.split(".")[0]),
                            {"appPackage": info["appPackage"], "appActivity": info["appActivity"][0]})
    return apk_info

def get_recdroid_apk_info():
    ori_apk_info = json.load(open("../Data/RecDroid/activity.txt", "r"))
    apk_info = {}
    for apk_name, info in ori_apk_info.items():
        apk_info.setdefault(int(apk_name.split(".")[0]),
                            {"appPackage": info["appPackage"], "appActivity": info["appActivity"][0]})
    return apk_info


def check_crash():
    # print("checking crash")
    log_file = open("../Temp/log/log_out.txt", "r", encoding="UTF-8", errors="ignore")
    log_lines = log_file.readlines()
    log_file.close()
    # for i in range(1,20):
    #     line = log_lines[-i]
    #     if len(line.strip()) > 0:
    #         print(line.strip())
    #         break
    for line in log_lines:
        if re.match(r".*?getText\(\) = Unfortunately, .*? has stopped.*", line):
            print(line)
            return True
        if re.match(r".*?W DropBoxManagerService: Dropping: data_app_crash.*?", line):
            print(line)
            return True
        if re.match(r".*?UiObject: getText\(\) = .*? isn't responding\..*?", line):
            print(line)
            return True
        if re.match(r".*?E AndroidRuntime: FATAL EXCEPTION: .*?", line):
            print(line.strip())
            return True
        if re.match(r".*?InputEventSender: Exception dispatching finished signal.*?", line):
            print(line.strip())
            return True
        if re.match(r".*?AnkiDroid: java\.util\.zip\.ZipException: File too short to be a zip file.*?", line):
            print(line.strip())
            return True
        if re.match(r".*?activity com.ichi2.anki.analytics.AnkiDroidCrashReportDialog has leaked.*?", line):
            print(line.strip())
            return True
        # if re.match(r".*?java.lang.RuntimeException: Unable to start activity ComponentInfo.*?", line):
        #     print(line.strip())
        #     return True

        # if re.match(r".*?WindowAnimator: android\.os\..*?Exception.*?", line):
        #     print(line.strip())
        #     return True
    return False


if __name__ == '__main__':
    # get_recdroid_apk_info()
    # get_andror2_apk_info()
    print(check_crash())
    pattern = re.compile("\[\d+]")
    s = "/android.widget.FrameLayout[1]/android.widget.ListView[1]/android.widget.LinearLayout[4]/andr"
    print(pattern.findall(s))
