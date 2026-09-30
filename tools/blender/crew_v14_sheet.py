"""Reference vs islander v14: hero shot and front/back/left/right, paired
(Pillow). Figures are cropped to their bounds and scaled to equal height."""
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
V14=ROOT/'crew-meshy-v14'
REF=Image.open(ROOT/'crew-islander-v9/reference.jpg').convert('RGB')
font=lambda b,s:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf'%('-Bold' if b else ''),s)


def fig(im,h,pad=0):
    bg=im.getpixel((3,3))
    box=ImageChops.difference(im,Image.new('RGB',im.size,bg)).convert('L').point(lambda v:255 if v>16 else 0).getbbox()
    im=im.crop(box);return im.resize((round(im.width*h/im.height),h),Image.LANCZOS)


def tile(im,w,h,bg):
    t=Image.new('RGB',(w,h),bg);t.paste(im,((w-im.width)//2,h-im.height-10));return t


BG=(95,142,178)
ref_views={'hero':REF.crop((0,40,660,1250)),'front':REF.crop((630,30,890,385)),'back':REF.crop((905,30,1165,385)),
           'left':REF.crop((690,420,880,785)),'right':REF.crop((930,420,1120,785))}
H1,H2=1000,470
sheet=Image.new('RGB',(2*(640+20)+4*(300+14)+60,H1+160),(28,40,46));d=ImageDraw.Draw(sheet)
x=20
for label,im in [('REFERENCE',ref_views['hero']),('BUILT: v14',Image.open(V14/'lit-hero.png').convert('RGB'))]:
    sheet.paste(tile(fig(im,H1-60),640,H1,BG),(x,90));d.text((x+10,30),label,font=font(1,40),fill=(235,225,200));x+=660
x+=20
for k,v in enumerate(['front','back','left','right']):
    xx=x+(k%2)*628;yy=90+(k//2)*(H2+40)
    ref=fig(ref_views[v],H2-40);me=fig(Image.open(V14/f'lit-{v}.png').convert('RGB'),H2-40)
    sheet.paste(tile(ref,300,H2,BG),(xx,yy));sheet.paste(tile(me,300,H2,BG),(xx+314,yy))
    d.text((xx+8,yy+H2+4),f'{v.upper()}: reference | v14',font=font(0,24),fill=(200,210,215))
sheet.save(V14/'reference-vs-v14.png')
