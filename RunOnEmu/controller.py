from appium import webdriver
import time
from appium.webdriver.common.mobileby import MobileBy
from appium.webdriver.common.touch_action import TouchAction
from RunOnEmu.xml_page_analyse import get_edittext_xpath, get_all_clickable_view, get_target_by_text
from UTG.states_and_views import StateViewInfo
from Recommend.util import clean_resource_id
from RunOnEmu.util import check_crash
import Levenshtein
import os
import re


class EmuRunner():
    def __init__(self, emu_info, state_view_info: StateViewInfo, app_reset=True):
        self.app_package = emu_info["appPackage"]
        self.app_reset = app_reset
        self.init_appium(emu_info, app_reset)
        self.state_view_info = state_view_info
        self.edittext_has_input = set()

    def init_appium(self, emu_info, app_reset):
        desired_caps = {}

        # # this is emu from android studio
        # desired_caps['platformName'] = 'Android'
        # desired_caps['platformVersion'] = '6.0'
        # desired_caps['deviceName'] = 'emulator-5554'
        # desired_caps['appPackage'] = emu_info["appPackage"]
        # desired_caps['appActivity'] = emu_info["appActivity"]
        # desired_caps['appActivity'] = emu_info["appActivity"]
        # desired_caps['noReset'] = "True"
        # desired_caps['dontStopAppOnReset'] = "True"
        # desired_caps['autoGrantPermissions'] = True
        # desired_caps['newCommandTimeout'] = 180

        # this is mumu emu
        # desired_caps['platformName'] = 'Android'
        # desired_caps['platformVersion'] = '6.0.1'
        # desired_caps['deviceName'] = '127.0.0.1:7555'
        # desired_caps['appPackage'] = emu_info["appPackage"]
        # desired_caps['appActivity'] = emu_info["appActivity"]

        # # this is emu from android 4.4
        # desired_caps['platformName'] = 'Android'
        # desired_caps['platformVersion'] = '4.4'
        # desired_caps['deviceName'] = 'emulator-5554'
        # desired_caps['appPackage'] = emu_info["appPackage"]
        # desired_caps['appActivity'] = emu_info["appActivity"]
        # desired_caps['appActivity'] = emu_info["appActivity"]
        # if not app_reset:
        #     desired_caps['noReset'] = "True"
        #     # desired_caps['dontStopAppOnReset'] = "True"
        # desired_caps['autoGrantPermissions'] = True
        # desired_caps['newCommandTimeout'] = 6000
        # desired_caps['automationName'] = 'UiAutomator1'

        # # this is emu from android 6/7
        desired_caps['platformName'] = 'Android'
        desired_caps['platformVersion'] = '7.0'
        desired_caps['deviceName'] = 'emulator-5554'
        desired_caps['appPackage'] = emu_info["appPackage"]
        desired_caps['appActivity'] = emu_info["appActivity"]
        desired_caps['appActivity'] = emu_info["appActivity"]
        if not app_reset:
            desired_caps['noReset'] = "True"
            # desired_caps['dontStopAppOnReset'] = "True"
        desired_caps['autoGrantPermissions'] = True
        desired_caps['newCommandTimeout'] = 6000
        desired_caps['automationName'] = 'UiAutomator2'

        self.driver = webdriver.Remote('http://localhost:4723/wd/hub', desired_caps)
        self.restart_app()

    def click_view(self, view_info):
        # print(view_info["xpath"])
        view_xpath = view_info["xpath"]
        ele = self.get_view_by_xpath(view_xpath) if len(view_xpath) > 10 else None
        if ele:
            ele.click()
        elif view_info["resource_id"] != None:
            ele = self.get_view_by_id(view_info["resource_id"])
            ele.click()
        else:
            target_bounds = view_info["bounds"]
            click_x = int((target_bounds[0][0] + target_bounds[1][0]) / 2)
            click_y = int((target_bounds[0][1] + target_bounds[1][1]) / 2)
            pos = (click_x, click_y)
            self.click_by_pos(pos)
        time.sleep(1)

    def click_view_by_xpath(self, view_key: str):
        if self.app_package == "pt.lighthouselabs.obd.reader" or self.app_package == "com.vestrel00.daggerbutterknifemvp":
            # this app click is slow by appium api
            # print("click by pos: obd.reader")
            click_view_info = self.state_view_info.views[view_key]
            target_bounds = click_view_info.bounds
            click_x = int((target_bounds[0][0] + target_bounds[1][0]) / 2)
            click_y = int((target_bounds[0][1] + target_bounds[1][1]) / 2)
            pos = (click_x, click_y)
            self.click_by_pos(pos)
            time.sleep(2)
            return True
        if "_Scroll" in view_key:
            return self.click_contain_scroll(view_key)
        view = self.state_view_info.views[view_key]
        long_click = False
        view_xpath = view_key
        if "###" in view_key:
            view_xpath = view_key.split("###")[1]
        if "_FillInfo" in view_xpath:
            view_xpath = view_xpath.replace("_FillInfo", "")
        if "_LongClick" in view_xpath:
            long_click = True
            view_xpath = view_xpath.replace("_LongClick", "")
        try:
            print(view_xpath)
            if long_click:
                ele = self.get_view_by_xpath(view_xpath)
                TouchAction(self.driver).long_press(ele).perform()
            else:
                ele = self.get_view_by_xpath(view_xpath)
                ele.click()
                # TouchAction(self.driver).tap(ele).perform()
            is_login1 = view.text.lower() in ["login", "log in", "sign in"]
            is_login2 = view.text.lower() == "next" and self.app_package == "com.fsck.k9.debug" and view.src_state == "state_2"
            if is_login1:
                time.sleep(3)
            elif is_login2:
                time.sleep(10)
            else:
                time.sleep(1)
                print("click done")
            return True
        except Exception as e:
            print(e)
            return False

    def long_click_view_by_xpath(self, view_xpath):
        # print(view_info["xpath"])
        view_xpath = view_xpath.split("_")[0]
        try:
            ele = self.get_view_by_xpath(view_xpath)
            TouchAction(self.driver).long_press(ele).perform()
            time.sleep(1)
            return True
        except Exception as e:
            print(e)
            cur_state, edittext_on_page, clickable_view_on_page = self.get_all_xpath_on_page()
            all_xpaths = []
            for edittext_xpath in edittext_on_page.keys():
                all_xpaths.append(edittext_xpath)
            for clickable_view_xpath in clickable_view_on_page.keys():
                all_xpaths.append(clickable_view_xpath)
            most_sim = 114514
            most_sim_xpath = all_xpaths[0]
            for xpath in all_xpaths:
                dis = Levenshtein.distance(view_xpath, xpath)
                if dis < most_sim:
                    most_sim = dis
                    most_sim_xpath = xpath
            if most_sim <= 3:
                print("find a similar xpath:", most_sim_xpath)
                return self.click_view_by_xpath(most_sim_xpath)
            else:
                print("### error: can't find view by xpath, discard")
                return False

    # def click_given_path(self):
    #     step_view_info = self.view_sim_res["step_view_info"]
    #     step_idxs = list(step_view_info.keys())
    #     step_idxs.sort()
    #     for step_idx in step_idxs:
    #         # print(step_view_info[step_idx])
    #         if step_view_info[step_idx]["may_match"] == 0:
    #             print("may match a wrong view, skip")
    #             continue
    #         target_view = step_view_info[step_idx]["view"]
    #         current_activity, page_source = self.get_page_info()
    #         cur_cluster = get_cluster_belong(current_activity, page_source, self.view_sim_res["cluster2id"],
    #                                          self.view_sim_res["id2detail"])
    #         self.detect_edittext_and_fill()
    #         if cur_cluster != target_view["src_cluster"]:
    #             transfer_views = self.view_sim_res["UTG"].get_transfer_path(cur_cluster, target_view["src_cluster"])
    #             for (transfer_view_key, from_cluster, to_cluster) in transfer_views:
    #                 try_time = 0
    #                 print(transfer_view_key)
    #                 while try_time < 3:
    #                     current_activity, page_source = self.get_page_info()
    #                     before_cluster = get_cluster_belong(current_activity, page_source,
    #                                                         self.view_sim_res["cluster2id"],
    #                                                         self.view_sim_res["id2detail"])
    #                     if before_cluster == from_cluster:
    #                         print("start match")
    #                     if "KEY#" in transfer_view_key:
    #                         self.click_back()
    #                     else:
    #                         print("123")
    #                         transfer_view = self.view_sim_res["all_views_short_dict"][transfer_view_key]
    #                         print("456")
    #                         self.click_view(transfer_view)
    #                         print("789")
    #
    #                     current_activity, page_source = self.get_page_info()
    #                     after_cluster = get_cluster_belong(current_activity, page_source,
    #                                                        self.view_sim_res["cluster2id"],
    #                                                        self.view_sim_res["id2detail"])
    #                     if after_cluster == to_cluster:
    #                         print("transfer done match")
    #                         self.detect_edittext_and_fill()
    #                         break
    #                     else:
    #                         try_time += 1
    #         print("click target_view:", target_view)
    #         self.click_view(target_view)
    #     self.simple_explore()

    def get_view_by_xpath(self, xpath):
        ele = self.driver.find_element(MobileBy.XPATH, xpath)
        return ele

    def get_view_by_id(self, id):
        ele = self.driver.find_elements(MobileBy.ID, id)
        return ele[0]

    def send_view_text_old(self, xpath, ori_content):
        before_state = self.get_current_state()
        try:
            ele = self.driver.find_element(MobileBy.XPATH, xpath)
            ele_id = ele.get_attribute("resourceId").split("/")[-1]
            ele_id = clean_resource_id(ele_id)
            content = self.get_special_input(ele_id, ori_content)
            is_password = "pass" in ele_id.split() or "password" in ele_id.split()
            if self.app_package != "com.beemdevelopment.aegis":
                print("before", ele.text)
                if ":" in ele.text and ele_id == "time":
                    return True
                if "/" in ele.text and ele_id == "date":
                    return True
                ele.send_keys(content)
            else:
                ele.click()
                input_cmd = "adb -s emulator-5554 shell input text " + content
                os.system(input_cmd)
                time.sleep(1)
            after_state = self.get_current_state()
            if before_state != after_state:
                print("back!")
                self.click_back()
                self.click_back()
            if self.app_package != "com.beemdevelopment.aegis":
                print("after", ele.text)
                if ele.text != " " and len(ele.text) < len(content) and not is_password:
                    ele.send_keys("111111111111")
                    print("retry input, send number", ele.text)
        except Exception as e:
            print(e)
            print(xpath)
            return False

    def send_view_text(self, xpath, ori_content):
        try:
            ele = self.driver.find_element(MobileBy.XPATH, xpath)
        except Exception as e:
            print(e)
            print(xpath)
            return False
        try:
            ele_id = ele.get_attribute("resourceId")
            if self.app_package != "com.beemdevelopment.aegis":
                ele_text = ele.text
            else:
                ele_text = "#" * 20
            if ele_id == None or type(ele_id) != type("a"):
                ele_id = "none"
            else:
                ele_id = ele_id.split("/")[-1]
            ele_id = clean_resource_id(ele_id)
            if ":" in ele_text and ele_id == "time":
                return True
            if "/" in ele_text and ele_id == "date":
                return True
            content = self.get_special_input(ele_id, ori_content, ele_text)
            # if ele_text == "20":
            #     content = "111111111111111"
            is_password = "pass" in ele_id.split() or "password" in ele_id.split()
            is_search = "search" in ele_id.split()

            if "\'" in content or "\"" in content or " " in content:
                print("use appium send key!")
                ele.send_keys(content)
            else:
                print("use adb cmd!")
                if self.app_package != "com.beemdevelopment.aegis":
                    default_content = ele.text
                else:
                    default_content = "#" * 20
                ele.click()
                move_cmd = "adb -s emulator-5554 shell input keyevent KEYCODE_MOVE_END"
                os.system(move_cmd)
                if not is_password:
                    ori_content_len = len(default_content) + 1
                else:
                    ori_content_len = 20
                is_default_digit = str(default_content).replace(" ", "").isdigit()
                # del_cmd = "adb -s emulator-5554 shell input keyevent --longpress 'KEYCODE_DEL 3'"
                del_cmd = "adb -s emulator-5554 shell input keyevent" + " KEYCODE_DEL" * ori_content_len
                os.system(del_cmd)
                input_cmd = "adb -s emulator-5554 shell input text \"" + content + "\""
                print("input cmd:", input_cmd)
                os.system(input_cmd)
                time.sleep(1)
            if self.app_package != "com.beemdevelopment.aegis":
                print("after", ele.text)
                if ele.text != " " and len(ele.text) < len(content) and not is_password:
                    input_cmd = "adb -s emulator-5554 shell input text \"11111111111\""
                    os.system(input_cmd)
                    print("retry input, send number", ele.text)
            if is_search:
                enter_cmd = "adb -s emulator-5554 shell input keyevent KEYCODE_ENTER"
                os.system(enter_cmd)
            self.edittext_has_input.add(xpath)
            return True
        except Exception as e:
            return False

    def click_by_pos(self, pos):
        self.driver.tap([pos])

    def click_back(self):
        self.driver.press_keycode(4)  # AndroidKeyCode for 'Back'
        time.sleep(2)

    def rotate_to_landscape(self):
        try:
            self.driver.orientation = "LANDSCAPE"
            time.sleep(1)
            if check_crash():
                return
            self.driver.orientation = "PORTRAIT"
        except Exception as e:
            return

    def get_page_info(self):
        return self.driver.current_activity, self.driver.page_source

    def get_pkg_name(self):
        page_source = self.driver.page_source
        match_obj = re.match(r".*package=\"([a-zA-Z.0-9]+)\".*", str(page_source))
        if match_obj:
            return match_obj.group(1)
        else:
            return "unknown"

    def detect_edittext_and_fill(self, content='HelloWorld'):
        current_activity, page_source = self.get_page_info()
        edittext_xpaths = get_edittext_xpath(page_source)
        for edittext_xpath in edittext_xpaths:
            if edittext_xpath not in self.edittext_has_input:
                self.send_view_text(edittext_xpath, content)
                self.edittext_has_input.add(edittext_xpath)
        self.edittext_has_input = set()

    # def simple_explore(self):
    #     current_activity, page_source = self.get_page_info()
    #     edittexts, clickable_views = get_all_clickable_view(page_source)
    #     for edittext in edittexts:
    #         edittext_xpath = edittext["xpath"]
    #         self.send_view_text(edittext_xpath, '11111111111111111')
    #     for clickable_view in clickable_views:
    #         if clickable_view["text"].lower() == "ok":
    #             self.click_view(clickable_view)

    def get_current_state(self):
        if self.app_package == "com.vestrel00.daggerbutterknifemvp":
            return "state_1"
        current_activity, page_source = self.get_page_info()
        cur_state = self.state_view_info.get_state_belong(current_activity, page_source)
        return cur_state

    def get_current_page_info(self):
        current_activity, page_source = self.get_page_info()
        save_file = open("save_xml.xml", "w", encoding="UTF-8")
        save_file.write(page_source)
        cur_state = self.state_view_info.get_state_belong(current_activity, page_source)
        edittext_on_page, clickable_view_on_page = get_all_clickable_view(page_source)
        return cur_state, edittext_on_page, clickable_view_on_page

    def get_all_xpath_on_page(self):
        current_activity, page_source = self.get_page_info()
        cur_state = self.state_view_info.get_state_belong(current_activity, page_source, print_sim=True)
        edittext_on_page, clickable_view_on_page = get_all_clickable_view(page_source)
        return cur_state, edittext_on_page, clickable_view_on_page

    def restart_app(self, reset=True):
        # self.driver.orientation = "PORTRAIT"
        # self.driver.close_app()
        # cmd1 = "adb -s emulator-5554 shell pm grant " + self.app_package + " android.permission.WRITE_EXTERNAL_STORAGE"
        # cmd2 = "adb -s emulator-5554 shell pm grant " + self.app_package + " android.permission.READ_EXTERNAL_STORAGE"
        # os.system(cmd1)
        # os.system(cmd2)
        # if self.app_package == "com.ichi2.anki" and self.app_reset:
        if self.app_package == "com.ichi2.anki":
            push_cmd = "adb -s emulator-5554 push ../Temp/AnkiDroid/ /sdcard/"
            os.system(push_cmd)
        if reset:
            # if self.app_package != "com.ichi2.anki" or self.app_reset:
            self.driver.reset()
        if self.app_package == "com.fsck.k9.debug":
            print("%%% push com.fsck.k9.debug")
            push_cmd = "adb  -s emulator-5554 root | adb -s emulator-5554 remount | adb  -s emulator-5554 push ../Temp/k9/com.fsck.k9.debug/ /data/data/"
            os.system(push_cmd)
        self.driver.launch_app()
        self.edittext_has_input = set()

    def save_screen_img(self, img_path: str):
        print("save screen img to:", img_path)
        self.driver.get_screenshot_as_file(img_path)

    def relaunch_app(self):
        # some app will return desktop, reopen it
        # main_acti = {"org.shadowice.flocke.andotp.dev": "org.shadowice.flocke.andotp.Activities.AuthenticateActivity"}
        # main_acti = {"org.shadowice.flocke.andotp.dev": "org.shadowice.flocke.andotp.Activities.MainActivity",
        #              "com.beemdevelopment.aegis": ".ui.MainActivity", "com.fsck.k9": ".activity.MessageList"}
        main_acti = {"com.fsck.k9": ".activity.MessageList"}
        if self.app_package not in main_acti.keys():
            return False
        print("### relaunch_app!!!!!")
        launch_cmd = "adb -s emulator-5554 shell am start " + self.app_package + "/" + main_acti[self.app_package]
        launch_p = os.popen(launch_cmd)
        launch_res = launch_p.read()
        if "Error" in launch_res:
            return False
        time.sleep(1)
        return True

    def get_special_input(self, edittext_id: str, input_content: str, ele_text: str):
        edittext_tokens = edittext_id.split()
        if "name" in edittext_tokens or "email" in edittext_tokens or "username" in edittext_tokens:
            if self.app_package == "com.example.terin.asu_flashcardapp":
                return "lu@gml.com"
            if self.app_package in ["com.fsck.k9.debug", "com.ichi2.anki"]:
                return "foobar20221234@outlook.com"
            if "@" not in input_content and self.app_package != "im.zom.messenger":
                return "foo@bar.com"
        if "secret" in edittext_tokens and self.app_package == "com.beemdevelopment.aegis":
            return "NBSWY3DPEB3W64TMMQ======"
        if "digits" in edittext_tokens:
            return "1"
        if "password" in edittext_tokens:
            if self.app_package == "com.example.terin.asu_flashcardapp":
                return "12331986"
            if self.app_package in ["com.fsck.k9.debug", "com.ichi2.anki"]:
                return "zaq13edc"
        if ele_text == "1 10":
            return "11111111111111"
        return input_content

    def swipe_down(self):
        self.driver.swipe(300, 1400, 300, 600)

    def click_contain_scroll(self, view_key):
        target_view = self.state_view_info.views[view_key]
        target_text = ""
        if target_view.text != "" and target_view.text != "none":
            target_text = target_view.text
        elif len(target_view.child_text) > 0:
            target_text = target_view.child_text[0][0]
        if target_text == "":
            print("### can't find target text by given view!")
            return False
        try_times = 0
        while try_times < 3:
            try_times += 1
            self.swipe_down()
            time.sleep(2)
            current_activity, page_source = self.get_page_info()
            click_pos = get_target_by_text(page_source, target_text)
            if click_pos[0] + click_pos[1] > 0:
                if "_LongClick" in view_key:
                    self.driver.tap([click_pos], duration=500)
                else:
                    self.driver.tap([click_pos])
                time.sleep(1.5)
                return True
        return False


if __name__ == '__main__':
    # a = os.system("adb -s emulator-5554 shell am start com.fsck.k9/.activity.MessageList")
    # print(type(a))
    # print(a)
    launch_p = os.popen("adb -s emulator-5554 shell am start com.fsck.k9/.activity.MessageList")
    launch_res = launch_p.read()
    print(launch_res)
    if "Error" in launch_res:
        print("### wrong")
