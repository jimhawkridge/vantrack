import pandas as pd
from datetime import *
import seaborn as sns

% matplotlib inline


posns = pd.read_csv('/home/jim/data/projects/vantrack/trk/posns.csv', delimiter='\t', header=None)
posns['dt'] = posns[3].map(lambda dt: datetime.strptime(dt.split('.')[0], '%Y-%m-%d %H:%M:%S'))
posns = posns[posns.dt > datetime(2017, 5, 2)]
posns = posns.set_index('dt')
posns

sampled = posns.resample('120T').count()[0]
sns.set_context('poster')
sampled.plot.line()

sns.set()
