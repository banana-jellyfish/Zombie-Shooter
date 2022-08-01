from typing import KeysView
import pygame
import numpy as np
from numba import njit
def main():
    pygame.init()
    screen = pygame.display.set_mode((800,600))
    running = True
    clock = pygame.time.Clock()
    hres = 120
    halfvres = 100
    mod = hres/60
    posx,posy,rot = 0,0,0
    frame = np.random.uniform(0,1,(hres,halfvres*2,3))
    sky = pygame.image.load('sky.jpg').convert()
    sky = pygame.transform.scale(sky,(700,360))
    sky = pygame.surfarray.array3d(pygame.transform.scale(sky,(360,halfvres*2)))
    floor = pygame.surfarray.array3d(pygame.transform.scale(pygame.image.load('wallimg4.png').convert(),(100,100)))

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        frame = new_frame(posx,posy,rot,frame,sky,floor,hres,halfvres,mod)
                # if int(x)%2 == int(y)%2:
                #     frame[i][halfvres*2-j-1] = [0,0,0]
                # else:
                #     frame[i][halfvres*2-j-1] = [1,1,1]
        surf = pygame.surfarray.make_surface(frame*255)
        surf = pygame.transform.scale(surf,(800,600))
        screen.blit(surf,(0,0))
        posx,posy,rot = movement(posx,posy,rot,pygame.key.get_pressed())
        pygame.display.update()
def movement(posx,posy,rot,keys):
    if keys[pygame.K_LEFT]:
        rot = rot-0.1
    if keys[pygame.K_RIGHT]:
        rot = rot+0.1
    if keys[pygame.K_w]:
        posx,posy = posx + np.cos(rot)*0.1, posy + np.sin(rot)*0.1
    if keys[pygame.K_s]:
        posx,posy = posx - np.cos(rot)*0.1, posy - np.sin(rot)*0.1
    return posx,posy,rot
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
            shade = 0.2+0.6*(1-j/halfvres)
            frame[i][halfvres*2-j-1] = shade*floor[xx][yy]/255
    return frame
if __name__ == '__main__':
    main()
    pygame.quit()