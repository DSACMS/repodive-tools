import argparse


parser = argparse.ArgumentParser(description='Metrics script to update data')
parser.add_argument('log_file')
args = parser.parse_args()

log_file = args.log_file

colors = [
  # Define a set of colors
  "#3357FF","#33FF57","#FAAAAA",
  "#FF33A1","#33FFF5", "#FFD733","#A133FF","#FF8C33","#DDFFDA","#3333AF"
]


associations = {}

with open(log_file, 'r') as f:
    log_lines = f.readlines()

current_color = 0
for line in log_lines:
    fields = line.split('|')
    path_parts = fields[3].split('/')

    base_dir = path_parts[1]
    #print(base_dir)
    if not associations.get(base_dir):
        associations[base_dir] = colors[current_color % len(colors)]
        current_color += 1
    
    color = associations[base_dir]
    new_line = line.strip() + f"|{color}"
    print(new_line)
