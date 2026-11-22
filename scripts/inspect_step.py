from build123d import import_step
from pathlib import Path
p=next(Path('data-bin').glob('*.step'))
a=import_step(p)
print('type',type(a), 'children',len(a.children),'solids',len(a.solids()),flush=True)
for i,s in enumerate(a.solids()):
 b=s.bounding_box(); print(i, 'size',tuple(round(x,3) for x in b.size), 'min',tuple(round(x,3) for x in b.min),'volume',round(s.volume,2),'faces',len(s.faces()), flush=True)
