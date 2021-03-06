import datetime

def print_msg(msg):
    print "{}: {}".format(get_time(), msg)

def get_time():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def check_bit(val, offset):
    mask = 1 << offset
    return (val & mask)
