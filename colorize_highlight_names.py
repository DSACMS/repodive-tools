import argparse


parser = argparse.ArgumentParser(description='Metrics script to update data')
parser.add_argument('log_file')
args = parser.parse_args()

log_file = args.log_file

colors = ["#474747","#E4E4E4"]


names = ["Brandon Yee", "Ricardo Zamora","CreativeNick"]

with open(log_file, 'r') as f:
    log_lines = f.readlines()


for line in log_lines:
    fields = line.split('|')
    #print(fields[1])
    for name in names:
        if name in fields[1]:
            color = colors[1]
            break
        else:
            color = colors[0]
            break
    
    new_line = line.strip() + f"|{color}"
    if color == colors[1] or (color == colors[0] and fields[2] != 'M'):
        print(new_line)
