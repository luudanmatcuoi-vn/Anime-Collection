import xlwings as xw
from xlwings import Range, constants
import config, logging

# Load Config và tạo logging
cfg = config.Config('config.ini')
logging.basicConfig(filename='logging.log',level=logging.INFO )
# set up logging to console
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)

# read excel
try:
	wb = xw.Book('data.xlsx')
except:
	wb = xw.Book()
	for t in cfg["new_database_form"].keys():
		wb.sheets.add(t)
		sheet = wb.sheets[t]
		sheet['A1'].value =  cfg["new_database_form"][t]
	try:
		sheet = wb.sheets["Sheet1"]
		sheet.delete()
	except:
		pass
	wb.save("data.xlsx")

def col(sheet,col_name):
	for i in range(1,20):
		if col_name == sheet[ (1,i) ].value: return i
	return False


def add_entry(sheet_name, file, row = False):
	sheet = wb.sheets[sheet_name]
	if row:
		row = int(row)
	else:
		row = sheet.range('A' + str(sheet.cells.last_cell.row)).end('up').row

	# sheet[( row, col(sheet,"id") )].value = idd
	row_key = sheet[(1,0)].expand("right").value
	write = []

	for r in row_key:
		if r in file.keys():
			write+=[file[r] ]
		else:
			write+=[None]
	sheet[(row,0)].expand("right").value = write


def get_sheet_data(sheet_name, condition={}):
	sheet = wb.sheets[sheet_name]
	i=2
	res = []
	row_key = sheet[(1,0)].expand('right').value

	temp = sheet[(0,0)].expand('table').value
	temp=temp[2:]

	for t in temp:
		file = {}
		for g in range(len(t)):
			if t[g]!=None:
				file[ row_key[g] ] = t[g]
		res+=[file]
	return res

def create_change_sheet(add_list,del_list,change_list):
	#Del change sheet if exist
	try:
		sheet = wb.sheets["Change"]
		sheet.delete()
	except:
		pass
	# Create change sheet
	for t in cfg["change_database_form"].keys():
		wb.sheets.add(t)
		sheet = wb.sheets[t]
		sheet['A1'].value =  cfg["change_database_form"][t]
	# idd = sheet.range('A' + str(sheet.cells.last_cell.row)).end('up').row-1 # Value để đánh stt vào
	row_id = 2

	row_key = sheet[(1,0)].expand('right').value

	# Write add_list
	for file in add_list:
		file["action"] = "ADD"
		write = []
		for r in row_key:
			if r in file.keys():
				write+=[file[r] ]
			else:
				write+=[None]
		sheet[(row_id,0)].expand("right").value = write

		# Highlight các entry có warning
		if file["warning"]:
			sheet["{}{}:{}{}".format("A",str(row_id+1),chr(65+len(row_key)-1),str(row_id+1))].color = (255,255,0)
		row_id+=1

	# Write del_list
	for file in del_list:
		file["action"] = "DEL"
		write = []
		for r in row_key:
			if r in file.keys():
				write+=[file[r] ]
			else:
				write+=[None]
		sheet[(row_id,0)].expand("right").value = write

		# Highlight tất cả các file delete
		sheet[(row_id, col(sheet,"warning") )].value = 1
		sheet["A{}:{}{}".format(str(row_id+1), chr(65+len(cfg["change_database_form"]["Change"][0])-1), str(row_id+1) )].color = (255,255,0)
		row_id+=1

	# Write change_list:
	for file in change_list:
		write = []
		for r in row_key:
			if r == 'action':
				write+=["CHANGE"]
			else:
				temp1 = str(file[0][r] or "")
				temp2 = str(file[1][r] or "")
				if temp2!=temp1:
					write += [ file[0][r]+"--==>"+file[1][r] ]
				else:
					write+=[file[1][r]]
		sheet[(row_id,0)].expand("right").value = write

		# Highlight tất cả các file Change
		sheet["A{}:{}{}".format(str(row_id+1), chr(65+len(cfg["change_database_form"]["Change"][0])-1), str(row_id+1) )].color = (255,255,0)
		row_id+=1

	#Tạo link
	create_link("Change")

def push():
	try:
		sheet = wb.sheets["Change"]
	except:
		return False

	# Get data from change sheet
	logging.info("Getting data from change sheet")
	change_sheet = get_sheet_data("Change")
	logging.info("Done get data from change sheet")

	# Add to list :)
	add_list = [f for f in change_sheet if f["action"]=="ADD"]
	for file in add_list:
		add_entry("Files",file)

	# Del entry from list
	del_list = [f for f in change_sheet if f["action"]=="DEL"]
	for file in reversed(del_list):
		# Lấy range
		file_sheet = wb.sheets["Files"]
		cell = file_sheet.api.UsedRange.Find(file["filename"]).Address
		row = cell.split("$")[-1]
		# Delete row
		file_sheet.range(row+':'+row).delete(shift='up')

	# Change entry from list
	change_list = [f for f in change_sheet if f["action"]=="CHANGE"]
	for file in reversed(change_list):
		# Lấy tên cần thay
		filesearch = file["filename"].split("--==>")
		file["filename"] = filesearch[1]
		filesearch = filesearch[0]
		# Lấy range
		file_sheet = wb.sheets["Files"]
		cell = file_sheet.api.UsedRange.Find(filesearch).Address
		row = cell.split("$")[-1]
		# EDIT row
		add_entry("Files",file, row = row)

	# Push xong thì chuyển Change sheet xuống cuối
	sheet.api.Move(None, After=wb.sheets["Anime"].api)

def create_link(sheet_name, exceptt = []):
	sheet = wb.sheets[sheet_name]
	last_row = sheet.range('A' + str(sheet.cells.last_cell.row)).end('up').row

	# File_link
	row_key = sheet[(1,0)].expand('right').value
	if "filename" in row_key and "file_link" not in row_key and "filename" not in exceptt:
		col_id = row_key.index("filename")
		sheet.range('{}:{}'.format(chr(65+col_id),chr(65+col_id) )).insert()
		sheet[(1,col_id)].value = "file_link"
		write = '=HYPERLINK({}{}&"\\"&{}{},"File")'.format(chr(65+col(sheet,"path")), 3, chr(65+col(sheet,"filename")), 3 )
		sheet[(2,col_id)].formula = write

		formulaa = sheet[(2,col_id)].formula 
		sheet.range('{}{}:{}{}'.format(chr(65+col_id), 3 ,chr(65+col_id), str(last_row+1) )).formula = formulaa

	# Mal Link
	row_key = sheet[(1,0)].expand('right').value
	if "mal_id" in row_key and "MAL_link" not in row_key and "mal_id" not in exceptt:
		col_id = row_key.index("mal_id")
		sheet.range('{}:{}'.format(chr(65+col_id),chr(65+col_id) )).insert()
		sheet[(1,col_id)].value = "MAL_link"
		write = '=HYPERLINK("https://myanimelist.net/anime/"&{}{},"Link")'.format(chr(65+col(sheet,"mal_id")), 3 )
		sheet[(2,col_id)].formula = write

		formulaa = sheet[(2,col_id)].formula 
		sheet.range('{}{}:{}{}'.format(chr(65+col_id), 3 ,chr(65+col_id), str(last_row+1) )).formula = formulaa

# create_link("Change")




# wb.save("data.xlsx")