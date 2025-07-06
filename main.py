import requests
import threading
import time
import datetime
import os


def print_up_master_info(csrf):
    try:
        data = requests.get(url=f"https://api.bilibili.com/x/web-interface/nav?csrf={csrf}", headers=hea).json()
        if data.get("code") == 0:
            name = data["data"].get("uname", "未知")
            mid = data["data"].get("mid", "未知")
            print("=" * 60)
            print(f"用户信息:\n  uid: {mid}\n  name: {name}")
            print("=" * 60)
            return True
        else:
            print("获取信息时出错，接口返回异常")
            return False
    except Exception as e:
        print(f"获取信息时出错: {e}")
        return False


def submit(reserve_id, ticket_no, title, csrf_token):
    resp = requests.post(url="https://api.bilibili.com/x/activity/bws/online/park/reserve/do", headers=hea,
                         data={"inter_reserve_id": reserve_id, "ticket_no": ticket_no, "csrf": csrf_token})
    try:
        print(f"{reserve_id}的预约结果:", resp.json())
    except Exception as e:
        print(f"出现异常{e},已启用自动重试")
        return 412
    if resp.json()["code"] == -702:
        return 702
    if resp.json()["code"] == 0:
        print(f"ID:{reserve_id} 活动:{title} 预约成功")
        return 0
    if resp.json()["code"] == 75574:
        print(f"ID:{reserve_id} 活动场次已空,线程已自动关闭")
        return 0
    return resp.json()["code"]


def _run(startTime, reserve_id, ticket_no, title, csrf_token):
    next_print_time = time.time()
    while True:
        now = time.time()
        remaining = startTime - now

        if remaining <= 0:
            break

        if now >= next_print_time:
            print(f"[提示] {reserve_id}距离开始还有 {int(remaining)} 秒\n")
            next_print_time = now + 30

        # 最后 1 秒内，每 10ms 检查一次
        sleep_time = 0.01 if remaining < 1 else 0.1
        time.sleep(sleep_time)
    while True:
        status = submit(reserve_id, ticket_no, title, csrf_token)

        if status == 0:
            break
        elif status == 412:
            continue
        elif status == 702:
            time.sleep(0.3)
            retry_status = submit(reserve_id, ticket_no, title, csrf_token)
            if retry_status == 0:
                break
            elif retry_status == 702:
                continue
            else:
                time.sleep(0.3)
        else:
            time.sleep(0.3)


def run():
    csrf_token = ""
    for line in cookie_str.split(";"):
        if line.split("=")[0].replace(" ", "") == "bili_jct":
            csrf_token = line.split("=")[1]
    if not print_up_master_info(csrf_token):
        print("登录失败,请检查您的Cookie输入")
        return False
    try:
        user_ipt = int(input("请输入要预约的类型(1为商品，0为活动)："))
        if user_ipt not in [0, 1]:
            print("错误输入!程序已退出")
            return False
    except ValueError:
        print("异常输入!程序已退出")
        return False

    req = requests.get(
        url=f"https://api.bilibili.com/x/activity/bws/online/park/reserve/info?csrf={csrf_token}&reserve_date=20250711,20250712,20250713&reserve_type={user_ipt}",
        headers=hea).json()
    if req["code"] != 0:
        print(f"哔哩哔哩API返回异常:{req}")
        return False
    day_info = input("请输入要购买的日期(填写20250711,20250712,20250713三选一)：")
    try:
        for item in req['data']['reserve_list'][day_info]:
            act_info[str(item["reserve_id"])] = item
            print("场次ID:{} 活动名:{} 开始时间:{} ".format(item["reserve_id"], item["act_title"],
                                                            datetime.datetime.fromtimestamp(
                                                                item["reserve_begin_time"]).strftime(
                                                                "%Y-%m-%d %H:%M:%S")))
    except KeyError:
        print(f"未查找到日期信息:{day_info},可能是您没有购买这一天的门票")
        return False
    for r_id in input("请输入活动ID(如913，多个活动ID请使用英文逗号,隔开，如913,916)：").split(","):
        try:
            item = act_info[r_id]
        except KeyError:
            print(f"ID:{r_id}不存在,已跳过")
            continue
        thread = threading.Thread(target=_run,
                                  kwargs={"startTime": item["reserve_begin_time"],
                                          "reserve_id": item["reserve_id"],
                                          "ticket_no": req['data']['user_ticket_info'][day_info]['ticket'],
                                          "title": item["act_title"], "csrf_token": csrf_token})
        thread.start()
        print(req['data']['user_ticket_info'][day_info]['ticket'], item["reserve_id"], "线程已启动\n")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("GitHub地址:https://github.com/MCQTSS/bws2025，由于作者已经抢到5080了就随缘开源出来了")
    print("=" * 60)
    cookie_str = input("请输入您账号的Cookie:")  # 用户输入Cookie
    act_info = {}
    hea = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,zh-TW;q=0.5,ja;q=0.4",
        "referer": "https://www.bilibili.com/blackboard/era/bws2025-event.html?native.theme=1&night=0",
        "priority": "u=1, i",
        "Cookie": cookie_str,
        "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1 Edg/137.0.0.0"
    }
    if not run():
        os.system("pause")
