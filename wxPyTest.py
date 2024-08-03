import wx

class PrimaryFrame(wx.Frame) :

    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called
        super(PrimaryFrame, self).__init__(*args, **kw)

        panel = PrimaryPanel(self)

    def OnExit(self, event):
        """Close the frame, terminating the application."""
        self.Close(True)


class PrimaryPanel(wx.Panel) :
	def __init__(self, parent) :
		super(PrimaryPanel, self).__init__(parent)

		#self.label = wx.StaticText(self, label="This is the Panel", pos = (100, 0))

		vbox = wx.BoxSizer(wx.VERTICAL)
		hbox = wx.BoxSizer(wx.HORIZONTAL)

		vbox.AddSpacer(20)

		self.label1 = wx.StaticText(self, label="Use buttons to Do Something or Cancel", style=wx.ALIGN_CENTER)
		vbox.Add(self.label1, 0, wx.EXPAND)

		self.btn1 = wx.Button(self, label="Do Something")
		hbox.Add(self.btn1, 0, wx.ALIGN_CENTER, 0)

		hbox.AddSpacer(20)

		self.btn2 = wx.Button(self, label="Cancel")
		hbox.Add(self.btn2, 0, wx.ALIGN_CENTER, 0)

		vbox.AddSpacer(100)

		vbox.Add(hbox, 0, wx.ALIGN_CENTER)

		self.btn1.Bind(wx.EVT_BUTTON, self.DoSomething)
		self.btn2.Bind(wx.EVT_BUTTON, self.Cancel)
		self.SetSizer(vbox)


	def DoSomething(self, event) :
		self.label1.SetLabelText("Text Has Been Changed")

	def Cancel(self, event) :
		self.parent.OnExit

		#gridsizer = wx.GridSizer(4,1,10,10)

		#for i in range(1,5) :
		#	btn = "Button " + str(i)
		#
		#	gridsizer.Add(wx.Button(self, label=btn), 0, wx.EXPAND)
		#
		#self.SetSizer(gridsizer)





class PrimaryApp(wx.App) :
	def OnInit(self) :
		self.frame = PrimaryFrame(parent = None, title = "This is the Frame title")
		self.frame.Show()

		return True



app = PrimaryApp()
app.MainLoop()