import os
import json
import random
import string
from datetime import datetime

MEMORY_FOLDER = "customer_memory"
INDEX_FILE = os.path.join(MEMORY_FOLDER, "kunden_index.json")

os.makedirs(MEMORY_FOLDER, exist_ok=True)

def generate_customer_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

def load_index():
    if not os.path.exists(INDEX_FILE):
        return {}
    with open(INDEX_FILE, "r") as f:
        return json.load(f)

def save_index(index):
    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)

def register_customer(name):
    index = load_index()
    if name in index:
        return index[name]
    new_id = generate_customer_id()
    index[name] = new_id
    save_index(index)
    return new_id

def get_customer_name_id_pairs():
    return load_index()

def list_customer_ids():
    index = load_index()
    return list(index.values())

def save_customer_data(customer_id, data):
    path = os.path.join(MEMORY_FOLDER, f"{customer_id}.json")
    memory = []
    if os.path.exists(path):
        with open(path, "r") as f:
            memory = json.load(f)
    memory.append({
        "timestamp": datetime.now().isoformat(),
        "content": json.dumps(data, indent=2)
    })
    with open(path, "w") as f:
        json.dump(memory, f, indent=2)

def save_customer_memory(customer_id, result):
    path = os.path.join(MEMORY_FOLDER, f"{customer_id}.json")
    data = []
    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)
    data.append({
        "timestamp": datetime.now().isoformat(),
        "content": result
    })
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def load_customer_memory(customer_id):
    path = os.path.join(MEMORY_FOLDER, f"{customer_id}.json")
    if not os.path.exists(path):
        return ""
    with open(path, "r") as f:
        data = json.load(f)
        return "\n\n".join([item["content"] for item in data])
