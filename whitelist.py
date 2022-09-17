import os
from shutil import move

def get_whitelisted_users(whitelist_file):
    if os.path.exists(whitelist_file):
        list_of_users  = [i.strip().replace("@", "") for i in open(whitelist_file).read().split("\n") if i.strip() != '' and i.strip() != '\n']
        return set(list_of_users)
    else:
        with open(whitelist_file, "a+") as f:
            f.write("")
        return set()

def add_whitelist_users(whitelist_file, whitelist_users, user_names):
    for user_name in user_names:
        user_name = user_name.replace("@", "")
        whitelist_users.add(user_name.lower())
    with open("tmp_file.txt", "w+") as f:
        f.write("\n".join([str(i) for i in whitelist_users]))
    move("tmp_file.txt", whitelist_file)


def remove_whitelist_users(whitelist_file, whitelist_users, user_names):
    for user_name in user_names:
        if user_name.lower() in whitelist_users:
            whitelist_users.remove(user_name.lower())
    with open("tmp_file.txt", "w+") as f:
        f.write("\n".join([str(i) for i in whitelist_users]))
    move("tmp_file.txt", whitelist_file)

