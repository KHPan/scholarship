import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow,
			QTableWidget, QTableWidgetItem,
			QWidget, QPushButton, QTextBrowser, QComboBox,
			QVBoxLayout, QHBoxLayout,
			QFontDialog, QFileDialog, QProgressDialog,
			QInputDialog, QMessageBox, QDialog)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QColor, QFont
from bs4 import BeautifulSoup
import requests
import webbrowser
import itertools
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, urljoin
from threading import Thread
from typing import Sequence, Tuple, Callable
import json
import re
from datetime import datetime

class ContentDialog(QDialog):
	def __init__(self, parent, url):
		super().__init__(parent)
		self.url = url
		self.result = None
		self.initUI(self.url)
	
	def addBtn(self, text: str, clicked: Callable[[None], None]
			) -> QPushButton:
		btn = QPushButton(self)
		btn.setText(text)
		btn.clicked.connect(clicked)
		return btn
	
	def onRemove(self):
		self.result = "Remove"
		self.close()
	
	def onRemoveAndNext(self):
		self.result = "RemoveAndNext"
		self.close()
	
	def onNext(self):
		self.result = "Next"
		self.close()

	def initUI(self, url: str):
		self.setWindowTitle("獎學金詳細資訊")
		self.resize(800, 600)
		self.setFont(self.parent().font)
		mainLayout = QVBoxLayout(self)

		buttonLayout = QHBoxLayout()
		buttonLayout.addWidget(self.addBtn("移除", self.onRemove))
		buttonLayout.addWidget(self.addBtn("移除並前往下一個", self.onRemoveAndNext))
		buttonLayout.addWidget(self.addBtn("下一個", self.onNext))
		mainLayout.addLayout(buttonLayout)

		textBrowser = QTextBrowser(self)
		re = requests.get(url)
		soup = BeautifulSoup(re.text, "lxml")
		table = soup.find("table", class_="blank-line-half")
		# 修改表格的style属性，添加格線样式
		table['style'] = "border: 1px solid black; border-collapse: collapse;"
		# 为表格中的每个td和th元素添加格線样式
		for td in table.find_all('td'):
			td['style'] = "border: 1px solid black;"
		for th in table.find_all('th'):
			th['style'] = "border: 1px solid black;"
		textBrowser.setHtml(table.prettify())
		textBrowser.anchorClicked.connect(self.openExternalLink)
		textBrowser.setSource = lambda x: None
		mainLayout.addWidget(textBrowser)

	def openExternalLink(self, url: QUrl):
		webbrowser.open(urljoin(self.url, url.toString()))

class LineQTableWidget(QTableWidget):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.setMouseTracking(True)
		self.lastHoveredRow = None

	def mouseMoveEvent(self, event):
		index = self.indexAt(event.pos())
		row = index.row()

		if self.lastHoveredRow is not None and self.lastHoveredRow != row:
			self.removeRowHighlight(self.lastHoveredRow)

		if row >= 0 and row != self.lastHoveredRow:
			self.setRowHighlight(row)
			self.lastHoveredRow = row

		super().mouseMoveEvent(event)

	def leaveEvent(self, event):
		if self.lastHoveredRow is not None:
			self.removeRowHighlight(self.lastHoveredRow)
			self.lastHoveredRow = None
		super().leaveEvent(event)

	def setRowHighlight(self, row):
		lightBlueColor = QColor('lightblue')
		for column in range(self.columnCount()):
			item = self.item(row, column)
			if item:
				item.setBackground(lightBlueColor)

	def removeRowHighlight(self, row):
		for column in range(self.columnCount()):
			item = self.item(row, column)
			if item:
				item.setBackground(Qt.white)

class MyMainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.record = []
		self.initUI()

	def onFontBtn(self):
		font, ok = QFontDialog.getFont(self.font, self)
		if ok:
			self.font = font
			self.setFont(self.font)
	
	def onFromUrl(self):
		dialog = QInputDialog(self)
		dialog.setInputMode(QInputDialog.TextInput)
		dialog.setWindowTitle("輸入網址")
		dialog.setLabelText("網址")
		dialog.setFont(self.font)

		# 显示对话框并获取输入结果
		if dialog.exec_() == QInputDialog.Accepted:
			url = dialog.textValue()
			self.setTable(url)
			self.record = []

	def onImport(self):
		filename, _ = QFileDialog.getOpenFileName(self, "Open File", "",
							"JSON Files (*.json)")
		if filename:
			with open(filename, "r") as f:
				dct = json.load(f)
				self.setTable(dct=dct)
			self.record = []
	
	def save(self, filename: str | None = None):
		if filename is None:
			if not hasattr(self, "filename"):
				return
		else:
			self.filename = filename
		dct = {"titles": self.titles, "chart": self.chart, "ids": self.ids,
			"start_dates": [ds.strftime("%Y/%m/%d")
					for ds in self.start_dates],
			"end_dates": [de.strftime("%Y/%m/%d")
					for de in self.end_dates]}
		with open(self.filename, "w") as f:
			json.dump(dct, f)

	def onExport(self):
		filename, _ = QFileDialog.getSaveFileName(self, "Save File", "",
							"JSON Files (*.json)")
		if filename:
			self.save(filename)

	def onBackward(self):
		if len(self.record) == 0:
			QMessageBox.information(self, "通知", "無上一步")
		else:
			row, chart, id, start_date, end_date = self.record.pop()
			self.chart.insert(row, chart)
			self.ids.insert(row, id)
			self.start_dates.insert(row, start_date)
			self.end_dates.insert(row, end_date)
			self.setTable()

	def addBtn(self, text: str, clicked: Callable[[None], None]
			) -> QPushButton:
		btn = QPushButton(self)
		btn.setText(text)
		btn.clicked.connect(clicked)
		return btn

	def openUrl(self, url: str) -> Tuple[Sequence[str],
						Sequence[Sequence[str]], Sequence[str],
						datetime, datetime]:
		titles = None
		chart = None
		ids = None
		def all_busy():
			nonlocal titles, chart, ids
			def getTitle():
				nonlocal titles
				re = requests.get(url)
				soup = BeautifulSoup(re.text, "lxml")
				titles = [t.getText() for t in
					soup.find("div", class_="list-result").find("table")
						.find("thead").find_all("td")]
			title_thread = Thread(target=getTitle)
			title_thread.start()
			
			def setChart(page: int, index: int):
				url_parts = urlparse(url)
				query_params = parse_qs(url_parts.query)
				query_params["pageIndex"] = page
				new_query_string = urlencode(query_params, doseq=True)
				new_url_parts = url_parts._replace(query=new_query_string)
				new_url = urlunparse(new_url_parts)
				re = requests.get(new_url)
				soup = BeautifulSoup(re.text, "lxml")
				tbody = (soup.find("div", class_="list-result")
						.find("table").find("tbody"))
				now_chart = [[td.getText() for td in tr.find_all("td")]
					for tr in tbody.find_all("tr")]
				if len(now_chart) > 0:
					charts[index] = now_chart
					ids[index] = [tr.get("id") for tr in tbody.find_all("tr")]

			A_TIME = 20
			charts = [None] * A_TIME
			ids = [None] * A_TIME
			index = 0
			while True:
				print(f"{index+1} to {index+A_TIME}")
				threads = []
				for _ in range(A_TIME):
					threads.append(Thread(target=setChart,
							args=(index+1, index)))
					threads[-1].start()
					index += 1
				for t in threads:
					t.join()
				if charts[-1] is None:
					break
				charts.extend([None] * A_TIME)
				ids.extend([None] * A_TIME)
			chart = list(itertools.chain(*[c for c in charts if c is not None]))
			ids = list(itertools.chain(*[i for i in ids if i is not None]))
			title_thread.join()
		progressDialog = QProgressDialog("正在爬蟲抓取...", "取消", 0, 0, self)
		progressDialog.setFont(self.font)
		progressDialog.setCancelButton(None)  # 選擇性：移除取消按鈕
		progressDialog.resize(300, 100)
		progressDialog.setStyleSheet("QProgressDialog {margin: 0px;} QProgressBar {border: 2px solid grey; border-radius: 5px; text-align: center;}")
		progressDialog.show()
		th_all = Thread(target=all_busy)
		th_all.start()
		while th_all.is_alive():
			QApplication.processEvents()
		progressDialog.close()
		start_date = []
		end_date = []
		for line in chart:
			dates = re.findall(r"\d{4}/\d{1,2}/\d{1,2}", line[2])
			start_date.append(datetime.strptime(dates[0], "%Y/%m/%d"))
			end_date.append(datetime.strptime(dates[1], "%Y/%m/%d"))
		return titles, chart, ids, start_date, end_date

	def onRemoveInvalid(self):
		now = datetime.now()
		removes = []
		for i, ed in enumerate(self.end_dates):
			if ed < now:
				removes.append(i)
		for i in reversed(removes):
			self.removeRow(i)

	def onSort(self, index: int):
		bit_lists = list(zip(self.chart, self.ids,
					   self.start_dates, self.end_dates))
		bit_lists.sort(key=lambda x: (x[index // 2 + 2],
								int(x[0][0]) * (1 - index % 2 * 2)),
				 reverse=index % 2 == 1)
		self.chart, self.ids, self.start_dates, self.end_dates\
			  = map(list, zip(*bit_lists))
		self.setTable()

	def initUI(self):
		self.font = QFont()
		self.font.setPointSize(15)
		self.setFont(self.font)
		self.setWindowTitle("獎學金程式")

		central_widget = QWidget(self)
		self.setCentralWidget(central_widget)
		mainLayout = QVBoxLayout(central_widget)

		buttonLayout = QHBoxLayout()
		buttonLayout.addWidget(self.addBtn("設定字體", self.onFontBtn))
		buttonLayout.addWidget(self.addBtn("網址匯入", self.onFromUrl))
		buttonLayout.addWidget(self.addBtn("檔案匯入", self.onImport))
		buttonLayout.addWidget(self.addBtn("檔案匯出", self.onExport))
		buttonLayout.addWidget(self.addBtn("回到上一步", self.onBackward))
		buttonLayout.addWidget(self.addBtn("移除過期", self.onRemoveInvalid))
		self.sortCombo = QComboBox(self)
		self.sortCombo.addItems(
			["按照開始日期排序(遞增)", "按照開始日期排序(遞減)",
				"按照結束日期排序(遞增)", "按照結束日期排序(遞減)"])
		self.sortCombo.currentIndexChanged.connect(self.onSort)
		buttonLayout.addWidget(self.sortCombo)
		mainLayout.addLayout(buttonLayout)

		self.table = LineQTableWidget(self)
		self.table.verticalHeader().setVisible(False)
		self.table.setSelectionBehavior(QTableWidget.SelectRows)
		self.table.cellClicked.connect(self.clickTable)
		mainLayout.addWidget(self.table)

		self.showMaximized()

	def setTable(self, url: str | None = None, dct: dict | None = None):
		if url is not None:
			self.titles, self.chart, self.ids,\
				 self.start_dates, self.end_dates = self.openUrl(url)
			self.onSort(self.sortCombo.currentIndex())
			return
		elif dct is not None:
			self.titles = dct["titles"]
			self.chart = dct["chart"]
			self.ids = dct["ids"]
			self.start_dates = [datetime.strptime(ds, "%Y/%m/%d")
					   for ds in dct["start_dates"]]
			self.end_dates = [datetime.strptime(de, "%Y/%m/%d")
					 for de in dct["end_dates"]]
		self.table.clear()
		self.table.setRowCount(len(self.chart))
		self.table.setColumnCount(len(self.titles))
		self.table.setHorizontalHeaderLabels(self.titles)
		for y, line in enumerate(self.chart):
			for x, cell in enumerate(line):
				self.table.setItem(y, x, QTableWidgetItem(cell))

	def removeRow(self, row):
		self.table.removeRow(row)
		self.record.append((row, self.chart[row], self.ids[row],
						self.start_dates[row], self.end_dates[row]))
		self.chart.pop(row)
		self.ids.pop(row)
		self.start_dates.pop(row)
		self.end_dates.pop(row)
		self.save()

	def clickTable(self, row, _):
		url = f"https://advisory.ntu.edu.tw/CMS/ScholarshipDetail?id={self.ids[row]}"
		dialog = ContentDialog(self, url)
		dialog.exec_()
		if dialog.result:
			if "Remove" in dialog.result:
				self.removeRow(row)
				row -= 1
			if "Next" in dialog.result:
				row += 1
				if row < len(self.chart):
					self.clickTable(row, None)

if __name__ == "__main__":
	app = QApplication(sys.argv)
	mainWindow = MyMainWindow()
	mainWindow.show()
	sys.exit(app.exec_())
