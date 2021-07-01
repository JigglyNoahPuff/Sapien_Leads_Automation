

data = [1, 2, 3, 4, 5, 6]

def add_two(n):
    return n + 2

new_data = map(add_two, data)
print(list(new_data))

