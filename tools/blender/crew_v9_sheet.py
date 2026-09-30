"""Turnaround sheet for islander v9, laid out like the reference it follows,
with the reference beside it for comparison (Pillow)."""
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont

OUT=Path(__file__).resolve().parents[2]/'crew-islander-v9'
font=lambda b,s:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf'%('-Bold' if b else ''),s)


def fit(name,w,h,pad=16):
    im=Image.open(OUT/name).convert('RGB');bg=im.getpixel((2,2))
    box=ImageChops.difference(im,Image.new('RGB',im.size,bg)).convert('L').point(lambda v:255 if v>12 else 0).getbbox()
    im=im.crop(box);k=min((w-2*pad)/im.width,(h-2*pad)/im.height)
    im=im.resize((round(im.width*k),round(im.height*k)),Image.LANCZOS)
    tile=Image.new('RGB',(w,h),bg);tile.paste(im,((w-im.width)//2,(h-im.height)//2));return tile


W,H=1400,1300
sheet=Image.new('RGB',(W,H),(111,147,168));d=ImageDraw.Draw(sheet)
sheet.paste(fit('neutral-front.png',720,1060),(20,20))
views=[('front.png','FRONT'),('back.png','BACK'),('left.png','LEFT'),('right.png','RIGHT')]
for k,(name,label) in enumerate(views):
    x=760+(k%2)*310;y=20+(k//2)*400
    sheet.paste(fit(name,300,350),(x,y));d.text((x+150,y+360),label,font=font(0,22),fill=(235,240,240),anchor='mm')
sheet.paste(fit('closeup.png',300,300,0),(760,830));d.text((910,1150),'HEAD / CHEST',font=font(0,22),fill=(235,240,240),anchor='mm')
sheet.paste(fit('game-size.png',300,300,40),(1070,830));d.text((1220,1150),'PHONE SIZE (2x)',font=font(0,22),fill=(235,240,240),anchor='mm')
d.text((40,1110),'SeaSick islander v9',font=font(1,40),fill=(245,245,240))
d.text((40,1165),'2,910 triangles · flat vertex colour · same 16-bone rig as the in-game crew',font=font(0,24),fill=(225,232,235))
sheet.save(OUT/'turnaround.png')
ref=Image.open(OUT/'reference.jpg').convert('RGB');ref=ref.resize((round(ref.width*H/ref.height),H),Image.LANCZOS)
both=Image.new('RGB',(ref.width+W+20,H+70),(28,40,46));both.paste(ref,(0,70));both.paste(sheet,(ref.width+20,70))
d=ImageDraw.Draw(both)
d.text((30,18),'REFERENCE (painted concept)',font=font(1,32),fill=(235,225,200))
d.text((ref.width+50,18),'BUILT: islander v9 (Blender preview)',font=font(1,32),fill=(235,225,200))
both.save(OUT/'reference-vs-v9.png')
