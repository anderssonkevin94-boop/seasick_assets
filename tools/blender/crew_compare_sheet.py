"""Side-by-side sheet: in-game v5, islander v6 and bean v8 (Pillow).

Each figure is cropped to its own bounds and scaled to the same height,
the way AstraPlaytestImport scales every crew model to 1.7 m in Unity.
Usage: python crew_compare_sheet.py <v5 renders dir>
"""
import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
V5=Path(sys.argv[1])
COLS=[('NOW IN GAME (v5)',V5),('v6 ISLANDER',ROOT/'crew-islander-v6'),('v8 BEAN',ROOT/'crew-bean-v8')]
H=620;GH=150;W=600


def figure(path,height):
    im=Image.open(path).convert('RGB')
    bg=Image.new('RGB',im.size,im.getpixel((0,0)))
    box=ImageChops.difference(im,bg).convert('L').point(lambda v:255 if v>12 else 0).getbbox()
    im=im.crop(box);figure.bg=bg.getpixel((0,0));return im.resize((max(1,round(im.width*height/im.height)),height),Image.LANCZOS)


font=lambda b,s:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf'%('-Bold' if b else ''),s)
views=[('neutral-front.png','front'),('neutral-rear.png','back')]
sheet=Image.new('RGB',(W*len(COLS),90+(H+40)*len(views)+60+GH*2+40),(34,52,58))
d=ImageDraw.Draw(sheet)
for c,(title,_) in enumerate(COLS):d.text((c*W+30,24),title,font=font(1,38),fill=(233,223,196))
y=90
for name,label in views:
    d.text((30,y+4),label,font=font(0,24),fill=(170,180,175));y+=36
    for c,(_,folder) in enumerate(COLS):
        f=figure(folder/name,H-60);tile=Image.new('RGB',(W-20,H),figure.bg)
        tile.paste(f,((tile.width-f.width)//2,30));sheet.paste(tile,(c*W+10,y))
    y+=H+4
d.text((30,y+10),'phone size: same height, shown 2x (game-size render)',font=font(0,24),fill=(170,180,175));y+=56
for c,(_,folder) in enumerate(COLS):
    f=figure(folder/'game-size.png',GH);tile=Image.new('RGB',(W-20,GH*2),figure.bg)
    f=f.resize((f.width*2,f.height*2),Image.NEAREST)
    tile.paste(f,((tile.width-f.width)//2,0));sheet.paste(tile,(c*W+10,y))
sheet=sheet.crop((0,0,sheet.width,y+GH*2+20))
sheet.save(ROOT/'crew-bean-v8/comparison.png')
