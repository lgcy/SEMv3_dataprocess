import json
import numpy as np
import cv2
import Polygon
import math
from utils.utils import parse_relation_from_table, get_span_cells, get_shared_line, get_shared_line_id, sort_shared_line, parse_gt_label, update_gt_label
import os
def cal_avg_text_hight(table):
    texts = table['line'] 
    all_text_h = []
    for text in texts:
        text = order_points_clockwise_list(text)
        x = text[0][0] - text[3][0]
        y = text[0][1] - text[3][1]
        height = math.sqrt((x**2)+(y**2))
        all_text_h.append(height)
    
        #import pdb;pdb.set_trace()
        #print(height)
        #text_polygon = Polygon.Polygon(text) 
        #all_text_h.append(text_polygon.height)
    avg_h = sum(all_text_h) / len(all_text_h)
    return avg_h

def order_points_clockwise_list(pts):
    #pts = pts.tolist()
    pts.sort(key=lambda x: (x[1], x[0]))
    pts[:2] = sorted(pts[:2], key=lambda x: x[0])
    pts[2:] = sorted(pts[2:], key=lambda x: -x[0])
    #pts = np.array(pts)
    return pts

def get_avg_point(point1, point2, avg_num):
    avg_points = []
    for i in range(1, avg_num):
        ratio = i / avg_num
        #print(ratio)
        x1, y1 = point1[0], point1[1]
        x2, y2 = point2[0], point2[1]
        x = round(x1 + ratio * (x2 -x1))
        y = round(y1 + ratio * (y2 -y1))
        avg_points.append([x,y])
    #print(point1, point2)
    return avg_points

def get_table(json_path):
    table = json.load(open(json_path, 'r'))
    table = parse_relation_from_table(table)
    ###获取跨行，跨列的单元格
    span_indice, row_span_indice, col_span_indice = get_span_cells(table['row_adj'], table['col_adj'])
    #import pdb;pdb.set_trace()
    shared_row_lines = get_shared_line(table['row_adj'], table['cell_adj'], table, row_span_indice)
    shared_col_lines = get_shared_line(table['col_adj'], table['cell_adj'], table, col_span_indice)


    #import pdb;pdb.set_trace()
    shared_row_line_ids = get_shared_line_id(table['row_adj'], table['cell_adj'], row_span_indice)
    shared_col_line_ids = get_shared_line_id(table['col_adj'], table['cell_adj'], col_span_indice)
    shared_row_line_ids, shared_row_lines, shared_col_line_ids, shared_col_lines = \
        sort_shared_line(shared_row_line_ids, shared_row_lines, shared_col_line_ids, shared_col_lines)
    #import pdb;pdb.set_trace()
    gt_label = parse_gt_label(table['cell_adj'], table['row_adj'], table['col_adj'], shared_row_line_ids, shared_col_line_ids)
    gt_label = update_gt_label(gt_label, table) # update transcripts for wired table
    return table, gt_label

def get_row_line_segmentatins(table, gt_label):
  ori_cells = table['cell']
  new_cells = gt_label['cells']
  num_row = len(table['row'])
  row_line_segmentations = []
  #import pdb;pdb.set_trace()
  for row_id in range(num_row + 1):
    print('now_row_id is:', row_id)
    now_row_line_segment = []

    #print('new_cell_id:', new_cell['cell_id'])
    if row_id == num_row:
       for new_cell in new_cells:
           cell_id = new_cell['cell_id']
           if len(cell_id) < 1:
               continue

           row_start_idx = new_cell['row_start_idx']
           row_end_idx = new_cell['row_end_idx']
           cell_id = int(new_cell['cell_id'])
           cell_box = ori_cells[cell_id]
           cell_box = order_points_clockwise_list(cell_box)
          
           if row_end_idx == row_id -1:
              now_row_line_segment.append(cell_box[3])
              now_row_line_segment.append(cell_box[2])
       if len(now_row_line_segment) > 0:
          row_line_segmentations.append(now_row_line_segment)
       continue

    for new_cell in new_cells:
        cell_id = new_cell['cell_id']
        if len(cell_id) < 1:
           continue

        row_start_idx = new_cell['row_start_idx']
        row_end_idx = new_cell['row_end_idx']
        cell_id = int(new_cell['cell_id'])
        cell_box = ori_cells[cell_id]
        cell_box = order_points_clockwise_list(cell_box)

        if row_start_idx == row_id:
           now_row_line_segment.append(cell_box[0])
           now_row_line_segment.append(cell_box[1])
           continue

        ###跨行的情况

        if row_end_idx >= row_id and row_start_idx < row_id:
           share_row_num = row_end_idx - row_start_idx + 1
           avg_points1 = get_avg_point(cell_box[0], cell_box[3], share_row_num)
           avg_points2 = get_avg_point(cell_box[1], cell_box[2], share_row_num)
           point_id = row_id - row_start_idx - 1
           now_row_line_segment.append(avg_points1[point_id])
           now_row_line_segment.append(avg_points2[point_id])
           #print('not complate')
    now_row_line_segment = sorted(now_row_line_segment, key= lambda x:x[0])
    if len(now_row_line_segment) > 0: 
       row_line_segmentations.append(now_row_line_segment)
  return row_line_segmentations  

def get_col_line_segmentatins(table, gt_label):

  ori_cells = table['cell']
  new_cells = gt_label['cells']
  num_col = len(table['col'])

  col_line_segmentations = []
  for col_id in range(num_col + 1):
    print('now_col_id is:', col_id)
    now_col_line_segment = []
    
    if col_id == num_col:
       for new_cell  in new_cells:

           cell_id = new_cell['cell_id']
           if len(cell_id) < 1:
               continue

           col_start_idx = new_cell['col_start_idx']
           col_end_idx = new_cell['col_end_idx']
           cell_id = int(new_cell['cell_id'])
           cell_box = ori_cells[cell_id]
           cell_box = order_points_clockwise_list(cell_box)

           if col_end_idx == col_id - 1:
              now_col_line_segment.append(cell_box[1])
              now_col_line_segment.append(cell_box[2])
       if len(now_col_line_segment) > 0:
          col_line_segmentations.append(now_col_line_segment)
       continue

    for new_cell in new_cells:

        cell_id = new_cell['cell_id']
        if len(cell_id) < 1:
           continue

        col_start_idx = new_cell['col_start_idx']
        col_end_idx = new_cell['col_end_idx']
        cell_id = int(new_cell['cell_id'])
        cell_box = ori_cells[cell_id]
        cell_box = order_points_clockwise_list(cell_box)

        if col_start_idx == col_id:
           now_col_line_segment.append(cell_box[0]) 
           now_col_line_segment.append(cell_box[3]) 

        ### 跨列的情况
       
        if col_end_idx >= col_id and col_start_idx < col_id:
           share_row_num = col_end_idx - col_start_idx + 1

           avg_points1 = get_avg_point(cell_box[0], cell_box[1], share_row_num)
           avg_points2 = get_avg_point(cell_box[3], cell_box[2], share_row_num)

           point_id = col_id - col_start_idx -1
           now_col_line_segment.append(avg_points1[point_id])
           now_col_line_segment.append(avg_points2[point_id])
    now_col_line_segment = sorted(now_col_line_segment, key= lambda x:x[1])

    if len(now_col_line_segment) > 0:
       col_line_segmentations.append(now_col_line_segment)
  return col_line_segmentations


data_dir = '/kanas/atlas/liugaocheng/iFLYTAB_data/11000-11999'
save_dir = './new-11000-11999'
all_files = os.listdir(data_dir)
num = 0
for file in all_files:
    if file.endswith('.json'):
       #file = '11473.json' 
       with open(os.path.join(data_dir,file)) as f:
           infos = json.load(f)
       is_wireless = infos['is_wireless']
       print('is_wireless:', is_wireless)
       if is_wireless:
          print('wireless not complate yet', file)
          continue
       label_path = os.path.join(data_dir, file)
       print('label_path:', label_path)
       table, gt_label = get_table(label_path)

       #import pdb;pdb.set_trace()   

       row_line_segmentations = get_row_line_segmentatins(table, gt_label)
       col_line_segmentations = get_col_line_segmentatins(table, gt_label)

       print('now_label_path:', label_path, len(row_line_segmentations), len(col_line_segmentations))
       row_start_center_bboxes = []
       print('row_line_segmentations:', row_line_segmentations)
       for row_line in row_line_segmentations:
          print('row_line-------:', row_line)
          ## 当前点为中心的8*8 正方形
          x1 = row_line[0][0] - 4
          y1 = row_line[0][1] - 4
          x2 = row_line[0][0] + 4
          y2 = row_line[0][1] + 4
          row_start_center_bboxes.append([x1, y1, x2, y2])

       col_start_center_bboxes = []
       print('col_line_segmentations:', col_line_segmentations)
       for col_line in col_line_segmentations:
          print('col_line:', col_line)
          x1 = col_line[0][0] - 4
          y1 = col_line[0][1] - 4
          x2 = col_line[0][0] + 4
          y2 = col_line[0][1] + 4
          col_start_center_bboxes.append([x1, y1, x2, y2])
       #import pdb;pdb.set_trace()
       img_name = file.split('.')[0] + '.png'
       img_path = os.path.join(data_dir, img_name)
       img = cv2.imread(img_path)
       h, w, c = img.shape

       avg_h = cal_avg_text_hight(table)
    

       gt_label["row_line_segmentations"] = row_line_segmentations
       gt_label["col_line_segmentations"] = col_line_segmentations
       gt_label["row_split_lines"] = row_line_segmentations
       gt_label["col_split_lines"] = col_line_segmentations

       gt_label["avg_text_h"] = avg_h
       gt_label["row_start_center_bboxes"] = row_start_center_bboxes
       gt_label["col_start_center_bboxes"] = col_start_center_bboxes
       gt_label["image_path"] = img_path
       gt_label["image_w"] = w
       gt_label["image_h"] = h
       gt_label["is_wireless"] = is_wireless
       save_path = os.path.join(save_dir, file)
       json.dump(gt_label, open(save_path, 'w'), indent=4)
#print(num)
'''
row_start_center_bboxes = []
for row_line in row_line_segmentations:
    ## 当前点为中心的8*8 正方形
    x1 = row_line[0][0] - 4
    y1 = row_line[0][1] - 4
    x2 = row_line[0][0] + 4
    y2 = row_line[0][1] + 4
    row_start_center_bboxes.append([x1, y1, x2, y2])

col_start_center_bboxes = []
for col_line in col_line_segmentations:
    x1 = col_line[0][0] - 4
    y1 = col_line[0][1] - 4
    x2 = col_line[0][0] + 4
    y2 = col_line[0][1] + 4
    col_start_center_bboxes.append([x1, y1, x2, y2])

avg_h = cal_avg_text_hight(table)
print(avg_h)
gt_label["row_line_segmentations"] = row_line_segmentations
gt_label["col_line_segmentations"] = col_line_segmentations
gt_label["row_split_lines"] = row_line_segmentations
gt_label["col_split_lines"] = col_line_segmentations


gt_label["avg_text_h"] = avg_h
gt_label["row_start_center_bboxes"] = row_start_center_bboxes
gt_label["col_start_center_bboxes"] = col_start_center_bboxes

json.dump(gt_label, open("new-12000-gt.json", 'w'), indent=4)
'''
