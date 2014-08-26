import wx

class RunEgoTraining(wx.Dialog):
    '''
    Run continuous egocentric training
    '''
    def __init__(self, maze, block_pos, *args, **kw):
        super(RunEgoTraining, self).__init__(*args, **kw)
        self.SetSize((400,300))

