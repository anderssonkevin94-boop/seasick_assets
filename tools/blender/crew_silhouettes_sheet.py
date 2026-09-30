"""Lays the crew_silhouettes_v7 renders out as one comparison sheet (Pillow)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT=Path(__file__).resolve().parents[2]/'crew-silhouettes-v7'
COLS=[('v6','NOW (v6)','reference'),('A-hauler','A  HAULER','wedge torso, big fists'),
      ('B-pear','B  PEAR','bell body, stubby arms'),('C-wiry','C  WIRY','lanky, stooped, long nose')]
CW,TOP=500,120
font=lambda b,s:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf'%('-Bold' if b else ''),s)
rows=[('front34',560),('front',560),('side',560),('phone',300)]
H=TOP+sum(h for _,h in rows)+40*len(rows)
img=Image.new('RGB',(CW*len(COLS),H),(236,229,213));d=ImageDraw.Draw(img)
for c,(key,title,sub) in enumerate(COLS):
    x=c*CW;d.text((x+30,22),title,font=font(1,40),fill=(28,36,40));d.text((x+30,72),sub,font=font(0,26),fill=(90,90,80))
y=TOP
labels={'front34':'three-quarter','front':'front','side':'side','phone':'phone size (~36 px): 4x | 1:1'}
for view,h in rows:
    d.text((30,y+6),labels[view],font=font(0,24),fill=(120,110,95));y+=40
    for c,(key,_,_) in enumerate(COLS):
        im=Image.open(OUT/f'{key}-{view}.png').convert('RGB')
        if view=='phone':
            img.paste(im.resize((160,176),Image.NEAREST),(c*CW+90,y+60));img.paste(im,(c*CW+330,y+120))
        else:img.paste(im,(c*CW,y))
    y+=h
for c in range(1,len(COLS)):d.line([(c*CW,0),(c*CW,H)],fill=(200,190,170),width=3)
img.save(OUT/'silhouettes.png')
