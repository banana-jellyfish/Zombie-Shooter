#importing buncha stuff
from cmath import tanh
import pygame, sys, math, pathfinding,random
from pygame.locals import *
import numpy as np
from numba import njit
#initialise python and fonts
pygame.init()
pygame.font.init()
#width and height in cells of the map
mapwidth = 30
mapheight =mapwidth
#max size an image can be
maxsize = 850
#getting info on the user's computer screen width and height
infoObject = pygame.display.Info()
#random flags, do something i don't know what
flags = FULLSCREEN | DOUBLEBUF
#setting up the surface to display things on
screen = pygame.display.set_mode((infoObject.current_w, infoObject.current_h),flags,16)
#width and height of screen
width = infoObject.current_w
height = infoObject.current_h
#setting up list for splitting images
splitimgs = []
#resolution, higher is faster, 1 is detailed but slow
resolution = 5
imgw = 100
imgh = 100
#how many pieces to split the image into
pieces = int(imgw/resolution)
while imgw%resolution != 0:
    imgw+=1
    pieces = int(imgw/resolution)
#function which returns a list of vertical slices of an image
def cut_img(image, pieces,width,height):
    image = pygame.transform.scale(image,(width,height))
    list_of_pieces = []
    pwidth = width/pieces
    for i in range(pieces+1):
        newimg = pygame.transform.chop(image,(0,0,width-(pwidth*i),0))
        newimg = pygame.transform.chop(newimg,(pwidth,0,pwidth*i,0))
        list_of_pieces.append(newimg)
    
    return list_of_pieces[ ::-1]
#images loaded for the dead zombies
dedzedimgs = []
deadzshadow = pygame.image.load('deadzshadow.png').convert_alpha()
for i in range(11):
    dedzedimg = pygame.image.load('deadzed.png').convert_alpha()
    for x in range(i):
        dedzedimg.blit(deadzshadow,(0,0))
    dedzedimgs.append(dedzedimg)
#now unused function which vertically cut images(tried to use it for the floor)
def cut_img_horizontal(image, pieces,width,height):
    image = pygame.transform.scale(image,(width,height))
    list_of_pieces = []
    pwidth = width/pieces
    for i in range(pieces+1):
        newimg = pygame.transform.chop(image,(0,0,0,height-(pwidth*i)))
        newimg = pygame.transform.chop(newimg,(0,pwidth,0,pwidth*i))
        list_of_pieces.append(newimg)
    
    return list_of_pieces[ ::-1]
#setting up slices list and using the function to cut each wall image into slices
slices = []
for i in range(5):
    image = pygame.image.load('wallimg'+str(i)+'.png').convert_alpha()
    image = pygame.transform.scale(image,(imgw,imgh))
    slices.append(cut_img(image,pieces,imgw,imgh))
#setting up blood list and adding all images blood splat goes through
bloods = []
numbloods = 5
for i in range(numbloods):
    bloodshade = []
    
    for x in range(11):
        img = pygame.image.load('blood'+str(i+1)+'.png').convert_alpha()
        img = pygame.transform.scale(img,(500,500))
        shadow = pygame.image.load('bloodshadow'+str(i+1)+'.png').convert_alpha()
        shadow = pygame.transform.scale(shadow,(500,500))
        for y in range(x):
            img.blit(shadow,(0,0))
        bloodshade.append(img)
    
    bloods.append(bloodshade)
    #opening the maze file and reading in the data
file = open('maze1.txt','r')
worldMap = file.readlines()
#function for splitting words
def split(word):
    list = []
    for char in word:
      if char != '\n':
          list.append(int(char))
    return list
#using function to create a 2d list for the world map
for i in range(len(worldMap)):
    charlist = split(worldMap[i])
    worldMap[i] = charlist
#setting up position variables
posX = 0
posY = 0
#setting up list of blood sprites
bloodsprites = []

#setting up a class for the blood sprites which just chooses what image they are pretty much
class blood:
    def __init__(self,x,y,offset,dist):
        self.x = x
        self.y = y
        self.image = bloods[0][10]
        self.bloodtime = 0
        self.dist = dist
        self.offset = offset
    def existence(self, bloodsprites,i):
        self.bloodtime += 1/10
        bloodimg = int(self.bloodtime*4)
        darkness = int(self.dist**2/6)
        if bloodimg >4:
            bloodimg = 4
        if darkness > 10:
            darkness = 10
        self.image = bloods[bloodimg][darkness]
        if self.bloodtime > 1:
            del bloodsprites[i]
# a lot of stuff in this class to tell monsters what to do
# class ammo:
#     def __init__(self,x,y):
#         self.x = x
#         self.y = y
#         self.dist = 0
#         self.startx = 0
#         self.width = 0
#         self.start = 0
#         self.end = 0
#         self.starty = 0
#     def check_collide(self,playerx,playery,ammosprites,ammo_count,ammonum):
#         o = self.x - playerx
#         a = self.y - playery
#         h = math.sqrt(o**2+a**2)
#         if h <= 1:
#             del ammosprites[ammonum]
#             ammo_count+=6
#         return ammosprites,ammo_count

class Monster:
    def __init__(self,posx,posy,damage,health, speed,zombieimage,bloods,type):
        #lotta variables
        self.num = 0
        self.shootable = False
        self.x = posx
        self.y = posy
        self.width = 0
        self.damage = damage
        self.health = health
        self.speed = speed
        self.zombieimage = zombieimage
        self.dist = 0
        self.start = -1
        self.end = -1
        self.drawn = False
        self.cooldown = 0
        self.pathfindcooldown = 0
        self.findingpath = False
        self.path = []
        self.rand_dirx = 0
        self.rand_diry = 0
        self.rand_dir_cooldown = 0
        self.visible = True
        self.bloods = bloods
        self.curr_blood = []
        self.bloodcooldown = 1 #secs
        self.numbloods = 0
        self.startx = 0
        self.starty = 0
        self.scale = 0
        self.type = type
        self.woundlist = []
    def check_collide(self,playerx,playery,ammosprites,ammo_count,ammonum):
        o = self.x - playerx
        a = self.y - playery
        h = math.sqrt(o**2+a**2)
        if h <= 1:
            del ammosprites[ammonum]
            ammo_count+=6
        return ammosprites,ammo_count
    def move(self,playerx,playery,playerrad,sprites,znum,res,frameTime):
            #decides where they go with pathfinding in separate file
            destx = playerx
            desty = playery
            o = self.x-playerx
            a = self.y-playery
            fullhyp = math.sqrt(o**2+a**2)
            if len(self.path) < 1:
                self.pathfindcooldown = 0
            if fullhyp >= 20 and self.start == self.end:
                self.findingpath = False
            if ((self.start != self.end) or self.findingpath) and self.pathfindcooldown<1:
                    self.path = pathfinding.astar(worldMap,(int(self.x)+0.5,int(self.y)+0.5),(int(playerx)+0.5,int(playery)+0.5))
                    if len(self.path) > 1:
                        del self.path[0]
                    self.pathfindcooldown = 60 
                    self.findingpath = True
                    if self.path[0] == 'no':
                        self.findingpath = False
            if self.findingpath:        
                destx = self.path[0][0]
                desty = self.path[0][1]
                
                o = destx - self.x
                a = desty - self.y
            if a == 0:
                a = 0.000000000000000000000000001

            angle = math.atan(o/a)
            hyp = self.speed
            newo = math.sin(angle)*hyp
            newa = math.cos(angle)*hyp
            if desty < self.y:
                newa = -newa
                newo = -newo
            
            if fullhyp >= playerrad and self.findingpath:
                newx = self.x+newo
                newy = self.y+newa
                move=True

                if move:
                        if worldMap[int(newx)][int(self.y)] == 0 or worldMap[int(newx)][int(self.y)] == 6:
                    
                        
                            self.x=newx
                        if worldMap[int(self.x)][int(newy)] == 0 or worldMap[int(self.x)][int(newy)] == 6:

                            self.y=newy
                if self.x > destx -0.2 and self.x < destx +0.2:
                    if self.y > desty -0.2 and self.y < desty +0.2:
                        if len(self.path) > 1:
                            del self.path[0]
            self.pathfindcooldown -= 1
    

 

    #checks if they can attack
    def check_attack(self,playerx,playery, health):
        o = -playerx+self.x
        a = -playery+self.y 
        fullhyp = math.sqrt(o**2+a**2)
        if fullhyp <= playerrad and self.cooldown < 1:
            health -= 1
            self.cooldown = 180
        return health
#sets up list of zombie images so they get darker further away

#sets what events are allowed
pygame.event.set_allowed([QUIT, KEYDOWN, KEYUP])
zomimg = pygame.image.load('zombie1.png').convert_alpha()
#image width and height
texWidth = 100
texHeight = 100
#gun image for aesthetics
gunimg = pygame.image.load('gun.png').convert_alpha()
gunwidth = width/2
gunimg = pygame.transform.scale(gunimg,(gunwidth,gunwidth))
numsprites = 10
#setting up lists for sprites
spriteOrder = [0]*numsprites
spritedist = [0]*numsprites
sprites = []
#checks where player is on map
for x in range(len(worldMap)):
    for y in range(len(worldMap[x])):
        if worldMap[x][y] == 7:
            posX = x+0.5
            posY = y+0.5 
#player radius
playerrad = 1
#title screen
def title(posX,posY,worldMap):
    titleimg = pygame.image.load('title.png')
    titleimg = pygame.transform.scale(titleimg,(width,height))
    while True:
        screen.blit(titleimg,(0,0))
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == KEYDOWN:
                if event.key == K_SPACE:
                    main(posX,posY,worldMap,resolution)
                if event.key == K_m:
                    mapeditor(mapwidth)
        pygame.display.update()
        #function for viewing/editing map and file
def mapeditor(mapwidth):
 foundpos = False
 for x in range(mapwidth):
    for y in range(mapheight):

        if worldMap[x][y] == 8:
            posX = x+0.5
            posY = y+0.5
            foundpos = True
            break
 if not foundpos:
    posX = 0.5
    posY = 0.5
    worldMap[0][0] = 8
 mousedown = False
 curr_colour = 1
 size = 1
 mapw = width/mapwidth
 maph = (0.9*height)/mapwidth
 mapzomimg = pygame.image.load('zombie1.png').convert_alpha()
 mapzomimg = pygame.transform.scale(mapzomimg,(mapw+1,maph+1))
 mapplayerimg = pygame.image.load('player.png').convert_alpha()
 mapplayerimg = pygame.transform.scale(mapplayerimg,(mapw+1,maph+1))
 mapammoimg = pygame.transform.scale(pygame.image.load('ammo1.png').convert_alpha(),(mapw+1,maph+1))
 mapwallimgs = []
 for i in range(5):
    wallimg = pygame.image.load('wallimg'+str(i)+'.png').convert_alpha()
    wallimg = pygame.transform.scale(wallimg,(mapw+1,maph+1))
    mapwallimgs.append(wallimg)
 
 mapwallimgs.append(mapammoimg)
 mapwallimgs.append(mapzomimg)
 mapwallimgs.append(mapplayerimg)
 myfont = pygame.font.SysFont('Arial', int(0.8*0.1*height))
 pygame.mouse.set_visible(False)
 while True:   
    screen.fill((0,0,0))
    
    #displaying map
    for x in range(mapwidth):
        for y in range(mapheight):
            if worldMap[x][y] > 0:
                screen.blit(mapwallimgs[worldMap[x][y]-1],(x*mapw,y*maph+(0.1*height)))
    mx,my = pygame.mouse.get_pos()
    if curr_colour > 0 and curr_colour < 8:
        for x in range(0,size*int(mapw+1),int(mapw+1)):
                    for y in range(0,size*int(maph+1),int(maph+1)):
                            screen.blit(mapwallimgs[curr_colour-1],(mx+x,my+y+int(0.1*height)))
    elif curr_colour == 8:
        screen.blit(mapwallimgs[curr_colour-1],(mx,my+int(0.1*height)))
    else:
        pygame.draw.rect(screen,(0,0,0),(mx,my+(0.1*height),mapw*size,maph*size))
    for i in range(8):
        
        textsurface = myfont.render((str(i+1)+':'), False, (255,255,255))
        screen.blit(textsurface,(int(i*(width/8)),int(0.1*0.1*height)))
        if i+1 == 6:
            placeimg = pygame.transform.scale(pygame.image.load('ammo1.png').convert_alpha(),(int(0.8*0.1*height),int(0.8*0.1*height)))
        elif i+1 == 7:
            placeimg = pygame.transform.scale(pygame.image.load('zombie1.png').convert_alpha(),(int(0.8*0.1*height),int(0.8*0.1*height)))
        elif i+1 == 8:
            placeimg = pygame.transform.scale(pygame.image.load('player.png').convert_alpha(),(int(0.8*0.1*height),int(0.8*0.1*height)))
        else:
            placeimg = pygame.transform.scale(pygame.image.load('wallimg'+str(i)+'.png').convert_alpha(),(int(0.8*0.1*height),int(0.8*0.1*height)))
        screen.blit(mapwallimgs[i],(int(i*(width/8)+width/16),int(0.5*0.1*height)))
    
    for event in pygame.event.get():
        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                #writing new map to file
                file = open('maze1.txt','w')
                for x in range(len(worldMap)):
                    for y in range(len(worldMap[x])):
                        file.write(str(worldMap[x][y]))
                        if y == mapwidth-1:
                            file.write('\n')
                file.close()
                title(posX,posY,worldMap)
                #getting key presses
            elif event.key == K_1:
                curr_colour = 1
            elif event.key == K_2:
                curr_colour = 2
            elif event.key == K_3:
                curr_colour = 3
            elif event.key == K_4:
                curr_colour = 4
            elif event.key == K_5:
                curr_colour = 5
            elif event.key == K_6:
                curr_colour = 6
            elif event.key == K_SPACE:
                curr_colour = 8
            elif event.key == K_7:
                curr_colour = 7
            if event.key == K_UP:
                size +=1
            elif event.key ==K_DOWN and size > 1:
                size -=1
            
            
        if event.type == MOUSEBUTTONDOWN:
            mousedown = True
        if event.type == MOUSEBUTTONUP:
            mousedown = False
    if pygame.mouse.get_pressed()[2]:
        curr_colour = 0
    if mousedown:
        #deciding where new colour should be
        mx,my = pygame.mouse.get_pos()
        mx = int(mx/mapw)
        my = int(my/maph)
        if curr_colour != 8:
            for x in range(size):
                if mx+x < mapwidth:
                    for y in range(size):
                        if my+y < mapwidth:
                            if (mx+x >0 and mx+x < mapwidth-1 and my+y > 0 and my+y < mapheight-1) or curr_colour >0:
                                worldMap[mx+x][my+y] = curr_colour
        else:
            if mx >0 and mx < mapwidth-1 and my > 0 and my < mapheight-1: 
                worldMap[int(posX)][int(posY)] = 0
                worldMap[mx][my] = curr_colour
                posX = mx+0.5
                posY = my+0.5
    
    pygame.display.update()
#main program
def main(posX,posY,worldMap,resolution):
    numz = 0
    sprites = []
    ashadow = pygame.transform.scale(pygame.image.load('ashadow.png').convert_alpha(),(50,50))
    zshadow = pygame.image.load('zshadow.png').convert_alpha()
    #removing monsters and player from map, and adding monsters to sprite list
    ammoimgs = []
    for i in range(11):
        ammoimg = pygame.image.load('ammo1.png').convert_alpha()
        ammoimg = pygame.transform.scale(ammoimg,(50,50))
        for x in range(i):
            ammoimg.blit(ashadow,(0,0))
        ammoimgs.append(ammoimg)
    fixedworldmap = worldMap
    for x in range(len(worldMap)):
        for y in range(len(worldMap[x])):
            if worldMap[x][y] == 6:
                a = Monster(x+0.5,y+0.5,0,0,0,ammoimgs,bloods,1)
                sprites.append(a)
                worldMap[x][y] = 0
            if worldMap[x][y] == 7:
                zombieimgs = []
                for i in range(11):
                    zimg = pygame.image.load('zombie1.png').convert_alpha()
                    for z in range(i):
                        zimg.blit(zshadow,(0,0))
                    zombieimgs.append(zimg)
                monsty = Monster(x+0.5,y+0.5,1,5,0.02,zombieimgs,bloods,0)
                sprites.append(monsty)
                numz+=1
                worldMap[x][y] = 0
            if worldMap[x][y] == 8:
                posX = x+0.5
                posY = y+0.5
                worldMap[x][y] = 0
    hres = 100
    halfvres = 100
    mod = hres/60
    rot = 0
    fram = np.random.uniform(0,1,(hres,halfvres*2,3))
    sky = pygame.image.load('sky.jpg').convert()
    sky = pygame.transform.scale(sky,(700,360))
    sky = pygame.surfarray.array3d(pygame.transform.scale(sky,(360,halfvres*2)))
    floor = pygame.surfarray.array3d(pygame.transform.scale(pygame.image.load('wallimg1.png').convert(),(100,100)))
    #a lot of variables
    health = 5  
    gameover = False
    numsprites = len(sprites)
    global screen
    shoot = False
    clock = pygame.time.Clock()
    #direction of player
    dirX = -1
    dirY = 0.0
    #camera plane
    planeX = 0.0
    planeY = 0.66
    #uses framerate to keep movement steady
    time = 0.0
    oldTime = 0.0
    fps = 60
    #movement buttons
    up = False
    down = False
    strafeleft = False
    straferight = False
    frameTime = fps
    pygame.font.init()
    #set up fonts
    myfont = pygame.font.SysFont('Arial', 30)
    #how large map cells on map are
    mapw = 200/mapwidth
    maph = 200/mapheight
    #position of mouse
    mx, my = pygame.mouse.get_pos()
    dir = 'none'
    frame = 0
    pygame.mouse.set_visible(False)
    texX = 100
    texY = 100
    oldtexnum = 0
    amount = 0
    startx = 0
    fpsnum = 0
    fpstotal = 0
    ammocount = 6
    reload =False
    unloaded_ammo = 4
    #images for the map
    mapzomimg = pygame.image.load('zombie1.png').convert_alpha()
    mapzomimg = pygame.transform.scale(mapzomimg,(mapw+1,maph+1))
    mapplayerimg = pygame.image.load('player.png').convert_alpha()
    mapplayerimg = pygame.transform.scale(mapplayerimg,(mapw+1,maph+1))
    mapwallimgs = []
    for i in range(5):
        wallimg = pygame.image.load('wallimg'+str(i)+'.png').convert_alpha()
        wallimg = pygame.transform.scale(wallimg,(mapw+1,maph+1))
        mapwallimgs.append(wallimg)
    mapwallimgs.append(mapzomimg)
    mapwallimgs.append(mapplayerimg)
    maxammo = 6
    woundimg = pygame.image.load('bullet_wound.png').convert_alpha()
    woundimg = pygame.transform.scale(woundimg,(5,5))
    #forever repeating game loop
    num_of_zombies = 0
    bshadow = pygame.image.load('bshadow.png').convert_alpha()
    while True:
        num_of_zombies = 0
        for i in range(len(sprites)):
            if sprites[i].type == 0:
                if sprites[i].health > 0:
                    num_of_zombies+=1
        walldists = []
        wallcols = []
        frame +=1
        win = False
        mx,my = pygame.mouse.get_pos()
        #finding out how far player has looked left or right with mouse
        pygame.mouse.set_pos(width/2,height/2)
        diffx = mx - width/2
        for i in range(len(sprites)):
            for x in range(len(sprites[i].curr_blood)):
                sprites[i].curr_blood[x][4] += diffx
        if diffx > 0 :
            dir = 'right'
        elif diffx < 0:
            dir = 'left'
        else:
            dir = 'none'
        diffx = abs(diffx)
        if diffx >20:
            diffx = 20
        #fill screen with black
        screen.fill((0,0,0))
        #goes through every [insert resolution]th pixel on screen
        fram = new_frame(-posX,posY,rot,fram,sky,floor,hres,halfvres,mod)
                # if int(x)%2 == int(y)%2:
                #     frame[i][halfvres*2-j-1] = [0,0,0]
                # else:
                #     frame[i][halfvres*2-j-1] = [1,1,1]
        surf = pygame.surfarray.make_surface(fram*255)
        surf = pygame.transform.scale(surf,(width,height))
        screen.blit(surf,(0,0))
        startx = 0
        amount = 0
        
        for x in range(0,(width+resolution),resolution):
            #i really don't understand much of this, got the maths from lodedevs tutorial
            cameraX = 2*x/float(width)-1
            rayDirX = float(dirX+planeX*cameraX)
            rayDirY = float(dirY+planeY*cameraX)
            if rayDirX == 0:
                rayDirX = 0.00000000000000000000001
            if rayDirY == 0:
                rayDirY = 0.00000000000000000000001
            mapX = int(posX)
            mapY = int(posY)
            sideDistX = 0
            sideDistY = 0
            if rayDirX == 0:
                deltaDistX = abs(1 / 1e30)
            else:
                deltaDistX = abs(1 / rayDirX)
            if rayDirY == 0:
                deltaDistY = abs(1 / 1e30)
            else:
                deltaDistY = abs(1 / rayDirY)
            perpWallDist = 0.1
            stepX = 0
            stepY = 0
            hit = 0
            side = 0
            if rayDirX < 0:
                stepX = -1
                sideDistX = (posX - mapX)*deltaDistX
            else:
                stepX = 1
                sideDistX = (mapX+1.0 - posX)*deltaDistX
            if rayDirY < 0:
                stepY = -1
                sideDistY = (posY-mapY)*deltaDistY
            else:
                stepY = 1
                sideDistY = (mapY+1.0 - posY)*deltaDistY
            while hit == 0:
                if sideDistX < sideDistY:
                    sideDistX += deltaDistX
                    mapX+=stepX
                    side= 0  
                else:
                    sideDistY += deltaDistY
                    mapY += stepY
                    #means wall is darker
                    side = 1
                if worldMap[int(mapX)][int(mapY)] > 0 and worldMap[int(mapX)][int(mapY)] < 6:
                    #means a walls been hit
                    hit = 1 
            if side == 0:
                perpWallDist = float(sideDistX - deltaDistX)
            else:
                perpWallDist = float(sideDistY - deltaDistY)
            h = height
            if perpWallDist <= 0:
                perpWallDist = 0.0001
            lineHeight = int(h/perpWallDist)
            #start of drawing(y)
            drawStart = int(-lineHeight / 2+h/2)
            #end of drawing(y)
            drawEnd = int(lineHeight/2+h/2)
            #how dark the wall is
            shade = int(perpWallDist**2)
            if side == 0:
                wallX = posY + perpWallDist * rayDirY
            else:
                wallX = posX + perpWallDist * rayDirX
            wallX -= math.floor((wallX))
            texX = int(wallX * (texWidth))
            if side == 0 and rayDirX > 0:
                texX = texWidth - texX - 1
            if side == 1 and rayDirY < 0: 
                texX = texWidth - texX - 1
            #which wall texture to use
            teximage = worldMap[int(mapX)][int(mapY)]-1
            # pygame.draw.line(screen,color,(x,drawStart),(x,drawEnd),resolution)
            texnum = int(texX/resolution)
            if oldtexnum != texnum or x == width:
                #if wall isn't completely black, draw slice of texture and put shade over that
                # if shade < 255:
                #how wide and tall texture is scaled to
                wideness = amount+resolution
                tallness = abs(drawEnd-drawStart)
                image = slices[teximage][oldtexnum] 
                divisor = tallness/100
                
                if drawStart < 0:
                    #chops image so top doesnt show  
                    stuff = abs(tallness-height)/divisor
                    
                    image = pygame.transform.chop(image,(0,0,0,abs(drawStart)/divisor))

                    drawStart = 0
                    tallness = height
                image = pygame.transform.scale(image,(wideness,tallness))
                screen.blit(image,(startx,drawStart))
                if shade > 1:
                    #darkens depending on how far away it is
                    s = pygame.Surface((amount+resolution,abs(drawEnd-drawStart)))  
                    s.set_alpha(shade)
                    s.fill((0,0,0))           
                    screen.blit(s, (startx,drawStart))
                if side == 1:
                    s = pygame.Surface((wideness,tallness))  
                    s.set_alpha(128)                
                    s.fill((0,0,0))           
                    screen.blit(s, (startx,drawStart))
                for i in range(resolution+amount):
                #find out how far each wall is to comapare it to monsters
                    walldists.append(perpWallDist)
                amount = 0
                startx = x
                
            else:
                amount += resolution
            oldtexnum = texnum
            
        checks = 1
        #put sprites in order by distance
        while checks > 0:
            checks = 0
            for i in range(len(sprites)-1):
                if sprites[i].dist< sprites[i+1].dist:
                    curr_spr = sprites[i]
                    replaced_spr = sprites[i+1]
                    sprites[i] = replaced_spr
                    sprites[i+1] = curr_spr
                    checks +=1
        checks = 1
        while checks > 0:
            checks = 0
            for i in range(len(bloodsprites)-1):
                if i < len(bloodsprites):
                    if bloodsprites[i].dist> bloodsprites[i+1].dist:
                        curr_spr = bloodsprites[i]
                        replaced_spr = bloodsprites[i+1]
                        bloodsprites[i] = replaced_spr
                        bloodsprites[i+1] = curr_spr
                        checks +=1
        for i in range(len(sprites)):
            #calculate things for drawing sprites
            
            spritex = sprites[i].x - posX
            spritey = sprites[i].y - posY
            invDet = 1.0 / (planeX*dirY-dirX*planeY)
            transformx = invDet*(dirY * spritex - dirX * spritey)
            transformy = invDet * (-planeY * spritex + planeX * spritey)
            if transformy == 0:
                transformy = 0.1
            vMove = 0.0
            if (sprites[i].health <= 0 and sprites[i].type == 0) or sprites[i].type == 1:
                vMove = 300
            vMoveScreen = int(vMove/transformy)
            if transformy == 0:
                transformy = 1
            spriteScreenX = int((width / 2) * (1 + transformx / transformy))
            spriteHeight = abs(int(height / (transformy)))
            if sprites[i].type == 1:
                spriteHeight/=2
            drawStartY = int(-spriteHeight / 2 + height / 2+vMoveScreen)
            drawEndY = int(spriteHeight / 2 + height / 2+vMoveScreen)
            if drawEndY >= height:
                 drawEndY = height - 1
            spriteWidth = spriteHeight
            drawStartX = int(-spriteWidth / 2 + spriteScreenX)
            # if drawStartX < 0:
                # drawStartX = 0
            drawEndX = int(spriteWidth / 2 + spriteScreenX)
            if drawEndX >= width:
                drawEndX = width-1
            if drawStartY < 0:
                 drawStartY = 0
            
            sprites[i].dist = transformy
            if spriteHeight > maxsize:
                spriteHeight =maxsize
                spriteWidth = maxsize
            darkness = int(sprites[i].dist/1.5)
            if sprites[i].type == 1:
                #because ammo is lower down so to prevent clashes with zombies and ammo
                sprites[i].dist-=0.5
            if darkness < 0:
                darkness = 0
            if darkness > 10:
                darkness = 10
            if sprites[i].type == 0:
                if sprites[i].health <= 0:
                    img = dedzedimgs[darkness]
                else:
                    img = sprites[i].zombieimage[darkness]
            else:
                img = sprites[i].zombieimage[darkness]
            # sprites[i].drawn = False
            sprites[i].startx = drawStartX
            sprites[i].starty = drawStartY  
            sprites[i].width = spriteWidth
            # sprites[i].visible = True
            if transformy > 0 and drawStartX > -spriteWidth:
                        starting = False
                        cut = False
                        sprites[i].start = 0
                        sprites[i].end = 0

                        for x in range(drawStartX,drawEndX):
                                if walldists[x] < sprites[i].dist:
                                    cut = True

                                else:
                                     if starting:
                                         sprites[i].end = x
                                     else:
                                         sprites[i].start = x
                                         starting = True
                        
                        # pwidth = width/pieces
                        # for i in range(pieces+1):
                        #     newimg = pygame.transform.chop(image,(0,0,width-(pwidth*i),0))
                        #     newimg = pygame.transform.chop(newimg,(pwidth,0,pwidth*i,0))
                        if spriteHeight < maxsize: 
                            # if cut:
                            img = pygame.transform.scale(img,(spriteWidth,spriteHeight))
                            # img = pygame.transform.chop(img,(0,0,spriteWidth-(sprites[i].start),0))
                            # img = pygame.transform.chop(img,(sprites[i].end-sprites[i].start,0,sprites[i].start,0))
                            # if sprites[i].start > drawStartX+spriteWidth:
                            #     screen.blit(img,(drawStartX,drawStartY),(sprites[i].start-drawStartX,0,sprites[i].end-sprites[i].start,spriteHeight))
                            # else:
                            #     screen.blit(img,(drawStartX,drawStartY),(0,0,sprites[i].end-sprites[i].start,spriteHeight))
                        
                            if drawStartX <= sprites[i].start:
                                screen.blit(img,(sprites[i].start-resolution,drawStartY),((sprites[i].start-drawStartX),0,sprites[i].end-sprites[i].start,spriteHeight))
                            else:
                                screen.blit(img,(drawStartX,drawStartY),(0,0,sprites[i].end-sprites[i].start-4,spriteHeight))
                        
                        # for x in range(len(sprites[i].woundlist)):
                        #     if sprites[i].startx+sprites[i].woundlist[x][0] >= sprites[i].start and sprites[i].startx+sprites[i].woundlist[x][0] <= sprites[i].end:
                        #         wound_image = pygame.transform.scale(woundimg,(int(spriteWidth/20),int(spriteHeight/20)))
                        #         screen.blit(wound_image,(sprites[i].startx+sprites[i].woundlist[x][0]+sprites[i].width/2,sprites[i].woundlist[x][1])) 
                        if sprites[i].start< width/2+(3/10*(sprites[i].start-sprites[i].end)) and sprites[i].end-resolution > width/2-(3/10*(sprites[i].start-sprites[i].end)):
                            sprites[i].shootable = True
                        else:
                            sprites[i].shootable = False                                # else:
                                #     img = pygame.transform.scale(img,(spriteWidth,spriteHeight))
                                #     screen.blit(img,(drawStartX,drawStartY))
        #animation of blood
        if len(bloodsprites) > 0:
            for i in range(len(bloodsprites)-1,-1,-1):
                bloodsprites[i].existence(bloodsprites,i)
                if len(bloodsprites) <= 0:
                    break
        #displaying blood sprites
        for i in range(len(bloodsprites)):
            spritex = bloodsprites[i].x - posX
            spritey = bloodsprites[i].y - posY
            invDet = 1.0 / (planeX*dirY-dirX*planeY)
            transformx = invDet*(dirY * spritex - dirX * spritey)
            transformy = invDet * (-planeY * spritex + planeX * spritey)
            if transformy == 0:
                transformy = 1
            spriteScreenX = int((width / 2) * (1 + transformx / transformy))
            spriteHeight = abs(int(height / (transformy)))
            drawStartY = int(-spriteHeight / 2 + height / 2)
            drawEndY = int(spriteHeight / 2 + height / 2)
            if drawEndY >= height:
                 drawEndY = height - 1
            spriteWidth = spriteHeight
            drawStartX = int(-spriteWidth / 2 + spriteScreenX)
            drawEndX = int(spriteWidth / 2 + spriteScreenX)
            if drawEndX >= width:
                drawEndX = width-1
            if drawStartY < 0:
                 drawStartY = 0
            img = bloodsprites[i].image
            bloodsprites[i].dist = transformy
            darkness = int(bloodsprites[i].dist/1.5)         
            if transformy > 0 and drawStartX > -spriteWidth and darkness < 10:
                        if spriteHeight > 500:
                            spriteHeight = 500
                            spriteWidth= 500
                        img = pygame.transform.scale(img,(spriteHeight,spriteWidth))
                        screen.blit(img,(drawStartX+bloodsprites[i].offset,drawStartY))
        pygame.draw.line(screen,(0,0,0),(width,0),(width,height),resolution)

        if not gameover:
            #display fps
            if frameTime != 0:
                textsurface = myfont.render('FPS: '+str(int(1/frameTime)), False, (255,255,255))
                screen.blit(textsurface,(250,0))
            if fpsnum > 600:
                fpsnum = 0
                fpstotal = 0
                #for the average fps
            fpsnum += 1
            fpstotal += 1/frameTime
            textsurface = myfont.render('Average FPS: '+str(int(fpstotal/fpsnum)), False, (255,255,255))
            screen.blit(textsurface,(750,0))
            textsurface = myfont.render('Health: '+str(health), False, (255,255,255))
            screen.blit(textsurface,(400,0))
            textsurface = myfont.render('Ammo: '+str(ammocount)+'|'+str(unloaded_ammo), False, (255,255,255))
            screen.blit(textsurface,(10,height-50))
            textsurface = myfont.render('Zombies: '+str(num_of_zombies), False, (255,255,255))
            screen.blit(textsurface,(width*0.8,height-50))
            pygame.draw.rect(screen,(0,0,0),(0,0,mapwidth*mapw,mapheight*maph))
        if not gameover:
            #display world map
            for x in range(mapwidth):
                for y in range(mapheight):
                    if worldMap[x][y] > 0:
                        screen.blit(mapwallimgs[worldMap[x][y]-1],(x*mapw,y*maph))
                    if x == int(posX) and y == int(posY):
                        screen.blit(mapwallimgs[6],(x*mapw,y*maph))
        if not gameover:
            screen.blit(gunimg,(width/2-(gunwidth/2)-6,height/2-(gunwidth/3)))
        # screen.blit(crosshair,(width/2-(cw/2),height/2-(cw/2)))
        oldTime = time
        time = pygame.time.get_ticks()
        frameTime = (time - oldTime)/1000
        moveSpeed = float(frameTime*5)
        rotSpeed = float(frameTime*diffx)/4
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            #handle key presses
            elif event.type == KEYDOWN:
                if event.key == K_UP:
                    resolution+=1
                if event.key == K_DOWN and resolution >1:
                    resolution-=1
                if event.key == K_w:
                    up = True
                    down = False
                
                if event.key == K_s:
                    down = True
                    up = False
                if event.key == K_r:
                    reload = True
                if event.key == K_d:
                    straferight = True
                    strafeleft = False
                if event.key == K_a:
                    strafeleft = True
                    straferight = False
                if event.key == K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                    #click mouse to shoot
            if event.type == MOUSEBUTTONDOWN and not gameover:
                    shoot = True
            elif event.type == KEYUP:
                if event.key == K_r:
                    reload = False
                if event.key == K_d:
                    straferight = False
                if event.key == K_a:
                    strafeleft = False
                
                if event.key == K_w:
                    up = False
                    
                if event.key == K_s:
                    down = False
            if event.type == MOUSEBUTTONUP:
                    shoot = False
        #for the player hitbox
        if dirX >=0:
            playradx = 0
        else:
            playradx = 0
        if dirY>=0:
            playrady = 0
        else:
            playrady = 0
        if up:
               #moving around     
                    if worldMap[int(posX+playradx+dirX*moveSpeed)][int(posY)] in[0,6]:
                        posX+=dirX*moveSpeed
                    if worldMap[int(posX) ][int(posY+playrady+dirY*moveSpeed)] in[0,6]:
                            posY+=dirY*moveSpeed
        if down:
                    
                    if worldMap[int(posX-playradx-dirX*moveSpeed) ][int(posY) ] in[0,6]:
                        posX-=dirX*moveSpeed
                    if worldMap[int(posX) ][int(posY-playrady-dirY*moveSpeed) ] in[0,6]:
                        posY-=dirY*moveSpeed
        if planeX >=0:
            playradx = 0
        else:
            playradx = 0
        if planeY>=0:
            playrady = 0
        else:
            playrady = 0
        if straferight:
                    
                    if worldMap[int(posX+playradx+planeX*moveSpeed) ][int(posY) ] in[0,6]:
                        posX+=planeX*moveSpeed
                    if worldMap[int(posX) ][int(posY+playrady+planeY*moveSpeed) ] in[0,6]:
                        posY+=planeY*moveSpeed
        if strafeleft:
                    
                    if worldMap[int(posX-playradx-planeX*moveSpeed) ][int(posY) ] in[0,6]:
                        posX-=planeX*moveSpeed
                    if worldMap[int(posX) ][int(posY-playrady-planeY*moveSpeed) ] in[0,6]:
                        posY-=planeY*moveSpeed
        if dir =='left':
                    oldDirX = dirX
                    dirX = dirX*math.cos(-rotSpeed)-dirY*math.sin(rotSpeed)
                    dirY = oldDirX * math.sin(rotSpeed)+dirY*math.cos(rotSpeed)
                    oldPlaneX = planeX
                    planeX = planeX*math.cos(rotSpeed)-planeY*math.sin(rotSpeed)
                    planeY = oldPlaneX * math.sin(rotSpeed)+planeY*math.cos(-rotSpeed)
                    rot-=(rotSpeed)
        if dir== 'right':
                    oldDirX = float(dirX)
                    dirX = dirX*math.cos(-rotSpeed)-dirY*math.sin(-rotSpeed)
                    dirY = oldDirX * math.sin(-rotSpeed)+dirY*math.cos(-rotSpeed)
                    oldPlaneX = float(planeX)
                    planeX = planeX*math.cos(-rotSpeed)-planeY*math.sin(-rotSpeed)
                    planeY = oldPlaneX * math.sin(-rotSpeed)+planeY*math.cos(-rotSpeed)
                    rot+=(rotSpeed)
            
        #shooting closest zombie in firing line
        if reload and not gameover and unloaded_ammo>0 and ammocount < maxammo:
            amount_to_reload = maxammo - ammocount
            if amount_to_reload > unloaded_ammo:
                amount_to_reload = unloaded_ammo
            ammocount+=amount_to_reload
            unloaded_ammo -= amount_to_reload
            reload = False
        if shoot and not gameover and ammocount >0:
            ammocount -=1
            if numz > 0:
                for i in range(len(sprites),-1,-1):
                    if sprites[i-1].type == 0:
                        if sprites[i-1].health > 0:
                            if sprites[i-1].shootable:
                            # if sprites[i-1].start+((3/10)*sprites[i-1].width) < width/2 and (sprites[i-1].startx+sprites[i-1].width)- ((3/10)*sprites[i-1].width) > width / 2:
                                sprites[i-1].health -= 1
                                pixel = (width/2-sprites[i-1].startx)/sprites[i-1].width*100
                                if pixel > 30 and pixel < 71:
                                    if pixel > 43 and pixel < 52:
                                        rng= random.randint(15,65)
                                    elif pixel > 39 and pixel <57:
                                        rng= random.randint(32,65)
                                    else:
                                        rng= random.randint(47,50)
                                    for x in range(11): 
                                        copyofzimage = sprites[i-1].zombieimage[x]
                                        woundimg = pygame.image.load('bullet_wound.png').convert_alpha()
                                        for j in range(x):
                                            woundimg.blit(bshadow,(0,0))
                                        copyofzimage.blit(woundimg,(((width/2-sprites[i-1].startx)/sprites[i-1].width*100),rng))
                                        sprites[i-1].zombieimage[x] = copyofzimage
                                    bloodsprites.append(blood(sprites[i-1].x,sprites[i-1].y,-sprites[i-1].width/2+(width/2)-sprites[i-1].startx,sprites[i-1].dist))
                                    if sprites[i-1].health < 1:
                                        sprites[i-1].zombieimage = dedzedimg
                                        numz -= 1
                                        sprites[i-1].woundlist = []

                                    break
                shoot = False
        if not gameover:
            #going through monster functions
            for i in range(len(sprites)):
                if i < len(sprites):
                    if sprites[i].type == 0:
                        if sprites[i].health > 0:
                            sprites[i].cooldown -= 1
                            sprites[i].move(posX,posY,playerrad,sprites,i,resolution,frameTime)
                            health = sprites[i].check_attack(posX,posY,health)
                    elif sprites[i].type == 1:
                        sprites,unloaded_ammo = sprites[i].check_collide(posX,posY,sprites,unloaded_ammo,i)

        if health <= 0:
            gameover = True
            #when ur dead
        if gameover:
            text  = myfont.render('YOU GOT EATEN UP', False, (0,0,0))
            bloodsurf = pygame.Surface((width,height))
            bloodsurf.set_alpha(128)
            bloodsurf.fill((255,0,0))
            screen.blit(bloodsurf,(0,0))
            screen.blit(text,(width/2,height/2))
        pygame.display.update()

        #keep steady framerate
        clock.tick(fps)  
@njit()
def new_frame(posx,posy,rot,frame,sky,floor,hres,halfvres,mod):
    for i in range(hres):
        rot_i = rot + np.deg2rad(i/mod-30)
        sin,cos,cos2 = np.sin(rot_i),np.cos(rot_i),np.cos(np.deg2rad(i/mod-30))
        frame[i][:] = sky[int(np.rad2deg(rot_i)%355)][:]/255
        for j in range(halfvres):
            n = (halfvres/(halfvres-j))/cos2
            x,y = posx+cos*n,posy +sin*n
            xx,yy = int(x*2%1*100),int(y*2%1*100)
            shade = 0.2+0.6*(1-j/(halfvres))
            frame[i][halfvres*2-j-1] = shade*floor[xx][yy]/255
    return frame
title(posX,posY,worldMap)
                
            
            

