import json

def get_cipher(text,i):
    with open(text, "r", encoding="utf-8") as f:
        file_content = f.read().strip()

    file_content = "{" + file_content + "}"
    data_dict = json.loads(file_content)

    return data_dict["c0_"+str(i)],data_dict["c1_"+str(i)]

def signed(v):
    s = []
    for _ in v:
        if(_ == 256):
            s.append(-1)
        else:
            s.append(_)
    return s

