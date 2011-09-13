#!/usr/bin/python
#coding=utf-8
import os
import re
import sys
import datetime
import socket
import urllib
import urllib2
import threading
from Queue import Queue
from BeautifulSoup import BeautifulSoup

flag = '' #更新还是下载的标志
comiclist = 'comic list.txt'
new = 'new.txt'
notDownloadAllList = [u'海贼王',u'结界师',u'火凤燎原'] #不用全部下载的漫画
THREAD_NUM = 15
q = Queue(0)
socket.setdefaulttimeout(30)
sys.stderr=file('error.log','w')

class my_thread(threading.Thread):

    def __init__(self,threadName):
        threading.Thread.__init__(self,name=threadName)
        self.f = file('comiclist.log','a')

    def run(self):
        while True:
            if q.empty():
                break
            tup =q.get()
            href = tup[0]
            sdir = tup[1]
            referer = href[:href.find('/showimage')]
            req = urllib2.Request(href)
            req.add_header('Referer',referer)
            try:
                #通过章节和页数获得图片的真实地址
                picurl = urllib2.urlopen(req).read().split(',')[0]
                #将图片地址进行编码（预防地址中有中文的情况）
                picurl = urllib2.quote(picurl).replace('%3A',':',1)
                index = picurl.rfind('/')+1
                #获取图片名
                picname = picurl[index:]
                picname =os.path.join(sdir,picname)
            except Exception,e:
                print >>self.f,datetime.datetime.now(),sdir.encode('utf-8','replace'),e,href
                self.f.close()
                q.put(tup)
                q.task_done
                continue
            try:
                if not os.path.exists(picname):
                    urllib.urlretrieve(picurl,picname)
                else:
                    q.task_done()
                    continue
            except Exception,e:
                print >>self.f,datetime.datetime.now(),sdir.encode('utf-8','replace'),e,href
                self.f.close()
                if os.path.exists(picname):
                    os.remove(picname)
                q.put(tup)
                q.task_done()
                continue
            print '%s download %s'%(self.getName(),picname)
            q.task_done()
           
def download(INDEX_URL):
    page_url = INDEX_URL 
    req = urllib2.Request(page_url)
    html = urllib2.urlopen(req).read()
    soup = BeautifulSoup(html)
    div = soup.find('div',{'class':'k1'})
    #每话都放在一个ul标签里面
    ul_list = div.findAll('ul',id=re.compile(r'cbc_\d+'))
    link_list = []   #链接,标题,页数
    for ul in ul_list:
        a_list = ul.findAll('a',href=re.compile(r'/m\d+/'))
        h_list = [a['href'].encode('ascii')[2:-1] for a in a_list] #链接
        t_list = [a['title'] for a in a_list] #标题
        #标题有重复的项在列表中的位置
        index_list = [i for i,t in enumerate(t_list) if t_list.count(t)>1]
        for i,index in enumerate(index_list):
            if index>1 and t_list[index]==t_list[index-1]:
                t_list[index]+='B'
        num_list = []  #页数
        li_list = ul.findAll('li')
        #找到每话的页数字符串
        for li in li_list:
            m = re.search(r'(\d+)页',li.text.encode('utf-8'))
            if m:
                num_list.append(m.group(1))
        if len(h_list)==len(t_list)==len(num_list):
            #链接,标题，页数列表
            link_list.extend(zip(h_list,t_list,num_list))
    maindir = soup.title.string.split('_')[0]
    if not os.path.exists(maindir):
        os.mkdir(maindir)
    for link in link_list:
        sdir = os.path.join(maindir,link[1])
        if maindir in notDownloadAllList and os.path.exists(sdir):
            return maindir
        if not os.path.exists(sdir):
            #记录更新的漫画话数
            if flag.strip()=='1':
                newComic = file(new,'a')
                newComic.write(link[1].encode('utf-8','replace')+'\n')
                newComic.close()
            os.mkdir(sdir)
        else:
            continue
        for i in range(1,int(link[2])+1):
            referer = "http://www.dm5.com/m%s-p%d"%(link[0],i)
            href ="%s/showimage.ashx?cid=%s&page=%s"%(referer,link[0],i)
            q.put((href,sdir))
        #将每话地址放入队列
        print q.qsize()
        #多线程
        threads=[]
        for i in range(THREAD_NUM):
            t = my_thread('thread %s'%(i+1))
            threads.append(t)
        for t in threads:
            t.setDaemon(True)
            t.start()
        q.join()
        for t in threads:
            t.join()
        print threading.activeCount()
        print 'finished',link[1]
        '''
        flag = raw_input('continue?y/n')
        if flag in ('n','N'):
            sys.exit()
        '''
    return maindir

def update():
    comic_list = open(comiclist).readlines()
    comic_list = [(line.split(' ')[0],line.split(' ')[1]) for line in comic_list]
    for comic in comic_list:
        download(comic[0])
        print 'finished update %s'%comic[1]

def main():
    global flag
    flag=raw_input('1.更新 2.下载新的漫画 3.退出:')
    print flag
    if flag==str(1):
        update()
        raw_input('finish update all')
    elif flag==str(2):
        indexurl = raw_input('输入漫画地址:').strip()
        comic_list = open(comiclist).readlines()
        comic_list = [line.split(' ')[0].strip() for line in comic_list]
        if indexurl in comic_list:
            raw_input('漫画已存在')
            sys.exit()
        title = download(indexurl)
        flag1 = raw_input('是否要写入更新列表？y/n:')
        if flag1 in ('y','Y'):
            try:
                f = open(comiclist,'a')
                f.write(indexurl+' '+title.encode('utf-8','repalce')+os.linesep)
                f.close()
            except Exception,e:
                print e.message
            else:
                print '写入更新列表成功'
            raw_input('finish download')
        else:
            raw_input('finfish download')
    else:
        sys.exit()

if __name__=='__main__':
   main() 
