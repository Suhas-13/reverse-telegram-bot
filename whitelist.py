import os

def get_whitelisted_users(whitelist_file):
    if os.path.exists(whitelist_file):
        list_of_users  = [i.strip() for i in open(whitelist_file).read().split("\n") if i.strip() != '' and i.strip() != '\n']
        return set(list_of_users)
    else:
        with open(whitelist_file, "a+") as f:
            f.write("")
        return set()

def add_whitelist_user(whitelist_file, whitelist_users, user_name):
    user_name = user_name.replace("@", "")
    whitelist_users.add(user_name)
    with open(whitelist_file, "a+") as f:
        f.write(user_name + "\n")

def remove_whitelist_user(whitelist_file, whitelist_users, user_name):
    if user_name in whitelist_users:
        whitelist_users.remove(user_name)
        with open("tmp_file.txt", "w+") as f:
            f.write("\n".join(whitelist_users))
        os.rename("tmp_file.txt", whitelist_file)

