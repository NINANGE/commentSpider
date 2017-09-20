# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import selenium.webdriver.support.ui as ui
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import time
import datetime
import requests
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import UnexpectedAlertPresentException
from pyquery import PyQuery as pq
import pymongo
from lxml import etree
import chardet
import pandas as pd
import re
import uuid
import urllib,urllib2
import base64
import json
import random
import os
from bs4 import BeautifulSoup
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
#验证接口
url = 'https://v2-api.jsdama.com/upload'

# allCategory = pd.read_csv('otherFile/taoBaoCategory.csv')

allCategory = pd.read_csv('/home/django/nange/commentSpider/otherFile/taoBaoCategory.csv')

# categoryUrl = 'https://detail.tmall.com/item.htm?id=17731025119'

client = pymongo.MongoClient('192.168.3.172',27017)
db = client.CommentDB
commentContentTB = db.commentContentTB
tableProject = db.commProjectTB
tableProjectDetail = db.commentCustomItemDetailTB



headers = {'UserAgent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.101 Safari/537.36'}

def commentSpider():

    # TODO:XDF Chrome欲歌浏览器
    # options = webdriver.ChromeOptions()
    #
    # # 设置中文
    # options.add_argument('lang=zh_CN.UTF-8')
    # prefs = {"profile.managed_default_content_settings.images": 2}
    # options.add_experimental_option("prefs", prefs)  # TODO:XDF 禁止加载图片
    # # 更换头部
    # options.add_argument(
    #     'user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.101 Safari/537.36"')
    # driver = webdriver.Chrome(chrome_options=options,executable_path=r'/Users/zhuoqin/Desktop/Python/SeleniumDemo/chromedriver')

    # TODO:XDF phantomjs无头浏览器
    dcap = dict(DesiredCapabilities.PHANTOMJS)
    dcap["phantomjs.page.settings.userAgent"] = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.101 Safari/537.36")  # 设置user-agent请求头
    dcap["phantomjs.page.settings.loadImages"] = False  # 禁止加载图片

    service_args = []
    service_args.append('--load-images=no')  ##关闭图片加载
    service_args.append('--disk-cache=yes')  ##开启缓存
    service_args.append('--ignore-ssl-errors=true')  ##忽略https错误

    driver = webdriver.PhantomJS(executable_path=r'/usr/bin/phantomjs',service_args=service_args, desired_capabilities=dcap) #TODO:XDF 针对Linux

    # driver = webdriver.PhantomJS(executable_path=r'/Users/zhuoqin/Desktop/Python/SeleniumDemo/phantomjs', desired_capabilities=dcap) #TODO:XDF 针对本地调试
    # wait = WebDriverWait(driver, 60, 0.5)  # 表示给browser浏览器一个10秒的加载时间
    #
    try:
        driver.implicitly_wait(30)
        driver.set_page_load_timeout(30)
    except Exception as e:
        print 'waitMiss-----%s'%e



    wait = WebDriverWait(driver, 200, 0.5)  # 表示给browser浏览器一个10秒的加载时间

    # projectData = tableProject.find({'Trailer_Tips': '待开启'})




    while True: #这里设置成死循环是因为项目一创建就启动爬虫，后面创建就不会执行，故：用死循环的方式进行检测
        projectData = tableProject.find({'Trailer_Tips': '正在爬取中...'})

        if projectData.count() > 0:
            print '当前有正在运行的爬虫，请稍后再启动...'
            break

        projectData = tableProject.find({'Trailer_Tips': { '$ne': '已过期'}} )

        if projectData.count() == 0:
            print '当前无可爬取任务，请知悉'
            break
            # return

        # 项目数据库
        for data in projectData:
            print '-----', data['ItemID'], projectData.count()
            updateProjectTBState(data['ItemID'], 'underWay')
            projectDetailData = tableProjectDetail.find({'ItemID': str(data['ItemID'])})
            for itemData in projectDetailData:
                # print itemData['ItemID']
                """
                    由于下面改变了编码格式为gbk，所以这里要重置编码为utf-8格式，否则第二次开始很多会变成乱码，例如 styleName参数
                """
                import sys
                reload(sys)
                sys.setdefaultencoding('utf-8')

                time.sleep(random.uniform(3,6))
                try:
                    driver.get('https://detail.tmall.com/item.htm?id=%s' % str(itemData['TreasureID']))
                    tmallLogin(driver)
                    time.sleep(random.uniform(3, 5))
                    tmallCode(driver, wait)
                except Exception as e:
                    print 'driver get error---%s'%e
                    continue


                #这里判断淘宝还是天猫，如果是淘宝，直接略过
                if ('item.taobao.com' in driver.current_url):# or (judgeProduct(driver) == True):
                    print 'taoBao,goOut...','存在'
                    productExist(itemData['ItemID'],str(itemData['ItemName']), str(itemData['TreasureID']), '3',datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))  # 不存在
                    continue
                if judgeProduct(driver) == True:
                    productExist(itemData['ItemID'],str(itemData['ItemName']),str(itemData['TreasureID']),'4',datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')) #不存在
                    continue
                if judgeProductOff(driver) == True:
                    productExist(itemData['ItemID'],str(itemData['ItemName']), str(itemData['TreasureID']), '2',datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))  # 不存在
                    continue

                else:
                    print 'tmall..', '不存在'

                try:
                    # wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'tb-detail-hd')))  # 显性等待
                    wait.until(EC.presence_of_element_located((By.ID,'J_AttrUL'))) # 显性等待
                    time.sleep(random.randint(3,5))
                except Exception as e:
                    print '显性未加载成功---%s' % e

                #判断是否已登录
                JudgeLoginSuccess(driver)
                time.sleep(random.uniform(3,5))
                html = driver.page_source
                # print html
                """
                    提取相关元素
                """
                provideSource(html,itemData,data)

            updateProjectTBState(data['ItemID'],'expire')

        #
        time.sleep(random.randint(3,8))



    print '结束完成'
    # time.sleep(2)
    # driver.quit()
    # driver.close()

"""
    提取相关元素
"""
def provideSource(html,itemData,data):
    try:
        doc = pq(html)
        spuIds = 'TShop.Setup\((.*?)\);'

        print '进来了'
        apiData = re.findall(spuIds, html, re.S)[0]

        datas = json.loads(apiData)
        print '获取内容--%s' % type(datas)
        # brand = doc.find('.J_EbrandLogo').text()
        brandId = datas['itemDO']['brandId']
        categoryId = datas['itemDO']['categoryId']
        rootCatId = datas['itemDO']['rootCatId']
        spuId = datas['itemDO']['spuId']
        title = datas['itemDO']['title']
        sellerId = datas['rateConfig']['sellerId']
        shopID = sellerId

        shopName = doc.find('.slogo-shopname').text()
        itemId = datas['rateConfig']['itemId']
        # 下面这两种都可以获取到
        # URL_NO = doc.find('#LineZing').attr('shopid')
        URL_NO = datas['rstShopId']
        ItemID = uuid.uuid1()
        TreasureLink = 'https://detail.tmall.com/item.htm?id=' + str(itemId)
        try:
            ShopURL = str(doc.find('.shopLink').attr('href'))
            print type(ShopURL)
            if len(ShopURL):
                ShopURL = ShopURL.replace('//', '')
            else:
                ShopURL = '-'
        except Exception as e:
            print e
        finally:
            print 'finish...'
        styleData = doc.find('#J_AttrUL').children().items()
        # 风格
        StyleName = styleNames(styleData)
        # 因为styleData是一个迭代器，被循环完的就会被释放掉（品牌有可能在查找风格的时候循环过去了，已经被释放掉了），所以这里得重新赋值数据源
        brandData = doc.find('#J_AttrUL').children().items()
        # 品牌
        brand = brandName(brandData)

        # 类目
        categoryName = categoryNames(categoryId)

        # 评价描述评分
        EvaluationScores = evaluationScoreURL(str(itemId), str(spuId), str(sellerId))

        detailContent = {
            'ItemID': ItemID,
            'TreasureID': str(itemId),
            'TreasureName': title,
            'TreasureLink': TreasureLink,
            'ShopName': shopName,
            'Shop_Platform': 1,
            'Treasure_Status': 1,
            'Monthly_Volume': 0,
            'IsMerge': 0,
            'MergeGuid': '',
            'Category_Name': categoryName,
            'GrpName': '',
            'spuId': spuId,
            'EvaluationScores': EvaluationScores,
            'ShopURL': ShopURL,
            'TreasureFileURL': '',
            'Url_No': URL_NO,
            'CategoryId': categoryId,
            'brandId': brandId,
            'brand': brand,
            'rootCatId': rootCatId,
            'StyleName': StyleName,
            'CollectionNum': 0,
            'ItemName': str(itemData['ItemName']),
            'InsertDate': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ModifyDate': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ShorName': '',
            'shopID': shopID
        }

        # SaveDetailContent(detailContent)

        updateCustomItemDetailTB(itemData['ItemID'],detailContent,'HaveInHand')

        lastPage = getLastPage(str(itemId), str(spuId), str(sellerId))

        print brand, brandId, categoryId, rootCatId, spuId, title, shopID, StyleName, shopName, itemId, categoryName, EvaluationScores, URL_NO, lastPage
        for page in range(1, lastPage + 1):
            print '第%s次' % page

            if commentContent(str(itemId), str(spuId), str(sellerId), str(page)):

                CommentData = commentContent(str(itemId), str(spuId), str(sellerId), str(page))["rateDetail"]["rateList"]
            else:
                continue

            # 获取所有评论内容并保存到mongodb
            getAllCommentData(CommentData, str(data['ItemID']), shopName, str(itemId), title, TreasureLink,
                              categoryName, str(itemData['ItemName']), EvaluationScores, data['ItemID'])

            time.sleep(random.randint(3,5))

        print brand, brandId, categoryId, rootCatId, spuId, title, shopID, StyleName, shopName, itemId, categoryName, EvaluationScores, URL_NO, lastPage
        updateCustomItemDetailTB(itemData['ItemID'],detailContent, 'productEnd')
    except Exception as e:
        print ('errorMISS---%s' % e)


"""
    判断是否已登录，未登录则先登录（这也是为了预防后面出现滑动验证），请知悉，反之，直接略过
"""
def JudgeLoginSuccess(driver):
    while True:
        time.sleep(2)
        if loginBtnExistence(driver) == True:
            print '还未登录'
            driver.find_element_by_xpath('//*[@id="login-info"]/a[1]').click()
            time.sleep(2)
            tmallLogin(driver)
        else:
            print '已登录'
            break

"""
    判断是否存在‘请登录’，存在就点击登录，反之，略过
"""
def loginBtnExistence(driver):
    try:
        if driver.find_element_by_xpath('//*[@id="login-info"]/a[1]').text == '请登录':
            loginBtn = True
        else:
            loginBtn = False
    except Exception as e:
        print 'loginMessage----%s'%e
        loginBtn = False
    return loginBtn


#TODO：XDF 产品是否存在或是否为淘宝或是否还未开始爬取
def productExist(ItemID,ItemName,TreasureID,Treasure_Status,InsertDate):
    try:
        if tableProjectDetail.update({'ItemID':ItemID,'TreasureID':TreasureID},{'$set':{'Treasure_Status':Treasure_Status,'ItemName':ItemName,'InsertDate':InsertDate}}):
            print 'UpdateS successful'
    except Exception as e:
        print 'update error---%s'%e

#更新详情表
def updateCustomItemDetailTB(ItemID,detailContent,state):
    print '详细内容---%s'%detailContent['TreasureName'], detailContent['TreasureLink'], detailContent['ShopName']#, rootCatId, spuId, title, shopID, StyleName, shopName, itemId, categoryName, EvaluationScores, URL_NO, lastPage
    try:
        if state == 'HaveInHand':
            Treasure_Status = '5'
        else:
            Treasure_Status = '1'

        if tableProjectDetail.update({'ItemID':ItemID,'TreasureID':detailContent['TreasureID']},{'$set':{'TreasureName':detailContent['TreasureName'],'TreasureLink':detailContent['TreasureLink'],
                                                                                'ShopName':detailContent['ShopName'],'Category_Name':detailContent['Category_Name'],'spuId':detailContent['spuId'],
                                                                                  'EvaluationScores':detailContent['EvaluationScores'],'ShopURL':detailContent['ShopURL'],
                                                                                  'Url_No':detailContent['Url_No'],'CategoryId':detailContent['CategoryId'],'brandId':detailContent['brandId'],
                                                                                  'brand':detailContent['brand'],'rootCatId':detailContent['rootCatId'],'StyleName':detailContent['StyleName'],
                                                                                  'ItemName':detailContent['ItemName'],'InsertDate':detailContent['InsertDate'],'ModifyDate':detailContent['ModifyDate'],
                                                                                  'shopID':detailContent['shopID'],'Treasure_Status':Treasure_Status
                                                                                  }}):
            print 'Update successful'
    except Exception as e:
        print 'update error---%s'%e

# 爬完一个项目下的所有产品ID，就更新一个当前项目的状态
def updateProjectTBState(ItemID,state):
    try:
        if state=='underWay':
            Trailer_Tips = '正在爬取中...'
        else:
            Trailer_Tips = '已过期'

        if tableProject.update({'ItemID': ItemID},{'$set':{'Trailer_Tips':Trailer_Tips}}):
            print 'updateProjectTB success'
    except Exception as e:
        print 'updateProjectTB error'

#判断这个产品是否已经不存在了
def judgeProduct(driver):
    try:
        driver.find_element_by_class_name('errorDetail')

        a = True

    except Exception as e:
        a = False
    return a

#判断这个产品是否已下架
def judgeProductOff(driver):
    try:
        driver.find_element_by_class_name('sold-out-tit')
        a = True
    except Exception as e:
        a = False
    return a

#风格
def styleNames(styleData):
    for data in styleData:
        print '数据-----%s'%data.text()
        if '风格: ' in data.text():
            StyleName = data.text().split(': ')[1]
            print ('风格---------------%s' % StyleName)
            break
        else:
            StyleName = '-'
    return StyleName

#类目
def categoryNames(categoryId):
    for k in range(0, len(allCategory)):
        if str(allCategory['CategoryId'][k]) == categoryId:
            categoryName = str(allCategory['CategoryName'][k])
            break
        else:
            categoryName = '-'
    return categoryName

#品牌
def brandName(brandData):

    for data in brandData:
        print '品牌选拔---%s' % data.text()
        if '品牌: ' in data.text():
            brand = data.text().split(': ')[1]
            print ('品牌---------------%s' % brand)
            break
        else:
            brand = '-'
    return brand

#中途可能需要登录
def tmallLogin(driver):
    if 'login.tmall' in str(driver.current_url):
        print ('需要登录----')
        # # TODO:XDF: 这是设置窗口大小（仅仅针对phantomjs无头浏览器，其它会报错）
        # driver.set_window_size(1800, 1000)
        driver.switch_to.frame("J_loginIframe")
        time.sleep(5)
        # TODO:XDF:1 因为无头浏览器是无界面的，所以只能通过截图来查看过程，下面同理（仅仅针对phantomjs无头浏览器，其它会报错）
        # driver.save_screenshot('RecordProcess/process1.png')

        if judgeHaveLogin(driver) == True:
            driver.find_element_by_xpath('//*[@id="J_Quick2Static"]').click()
        else:
            print '----NO_Click----'

        time.sleep(2)
        # TODO:XDF:2
        # driver.save_screenshot('RecordProcess/process2.png')
        driver.find_element_by_name("TPL_username").clear()
        driver.find_element_by_name("TPL_username").send_keys("13672456277")
        driver.save_screenshot('/home/django/nange/commentSpider/screenshot/loginUsername.png')
        time.sleep(random.uniform(3, 4))
        driver.find_element_by_name("TPL_password").clear()
        driver.find_element_by_name("TPL_password").send_keys("248552ZZN")
        driver.save_screenshot('/home/django/nange/commentSpider/screenshot/loginPassword.png')
        time.sleep(random.uniform(3, 4))
        # driver.save_screenshot('screenshot/login.png') #测试
        driver.save_screenshot('/home/django/nange/commentSpider/screenshot/login.png')
        #
        # TODO:XDF:3
        # driver.save_screenshot('RecordProcess/process3.png')
        driver.find_element_by_xpath('//*[@id="J_SubmitStatic"]').click()
        # TODO:XDF:4
        # driver.save_screenshot('RecordProcess/process4.png')
        # loginBtn.send_keys(Keys.RETURN)
        print ('login success')
        # driver.save_screenshot('RecordProcess/process5.png')
        time.sleep(2)

#判断是否包含‘密码登录’字样，如果有需要执行点击，反之不需要
def judgeHaveLogin(driver):
    try:
        if driver.find_element_by_xpath('//*[@id="J_QRCodeLogin"]/div[@class="login-links"]/a[@class="forget-pwd J_Quick2Static"]').text:
            a = True
            print '内容---%s' % driver.find_element_by_xpath('//*[@id="J_QRCodeLogin"]/div[@class="login-links"]/a[@class="forget-pwd J_Quick2Static"]').text
        else:
            print '内容2---%s' % driver.find_element_by_xpath('//*[@id="J_QRCodeLogin"]/div[@class="login-links"]/a[@class="forget-pwd J_Quick2Static"]').text
            a = False
    except Exception as e:
        print 'loginError ---%s'%e
        a = False
    return a

#TODO:XDF 验证码验证（通过打码平台）
def tmallCode(driver,wait):
    if 'sec.taobao.com' in driver.current_url:
        while True:
            print '需要验证码'
            wait.until(EC.presence_of_element_located((By.ID, 'checkcodeImg')))
            detailCode = pq(driver.page_source)
            picURL = detailCode.find('#checkcodeImg').attr('src')

            if 'https:' in picURL:
                imageURL = picURL
            else:
                imageURL = 'https:' + picURL
            print '图片地址---%s' % imageURL
            save_img(imageURL, 'picDic/picDic.png')

            driver.find_element_by_xpath('//*[@id="checkcodeInput"]').clear()

            # 设置要请求的头，让服务器不会以为你是机器人
            headers = {'UserAgent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.101 Safari/537.36'}
            f = open('picDic/picDic.png', 'rb')  # 二进制打开图文件 CrawlResult/1111.png
            ls_f = base64.b64encode(f.read())  # 读取文件内容，转换为base64编码
            f.close()
            values = {"softwareId": 7616, "softwareSecret": "p2AXUYMaTDcV72UoULYQQt7ubVPwTUXXlXIw7A3S",
                      "username": "ZZN_1993", "password": "@ZHOUZEnan1993", "captchaData": ls_f,
                      "captchaType": 1017,
                      "captchaMinLength": 4, "captchaMaxLength": 8}  # @ZHOUZEnan1993
            data = json.dumps(values)
            # 发送一个http请求
            request = urllib2.Request(url=url, headers=headers, data=data)
            # 获得回送的数据
            response = urllib2.urlopen(request)

            datas = eval(response.read())
            print 'data---%s---%s--%s--%s' % (datas['code'], datas['message'], datas['data']['recognition'], datas['data']['captchaId'])
            code = str(datas['data']['recognition']).replace('\r\n', '').replace(' ', '').replace('\n', '').replace('\t','')
            driver.find_element_by_xpath('//*[@id="checkcodeInput"]').send_keys(code)

            driver.find_element_by_xpath('//*[@id="query"]/div[@class="submit"]/input').click()
            time.sleep(2)
            print '测试结束************'
            # continue

            if judgeProdctCode(datas) == True:
                print '验证码错误，继续下载识别'
            else:
                break


#判断验证错是否验证错误
def judgeProdctCode(datas):
    try:
        datas.find('#tip .error').text()
        code = True

    except Exception as e:
        print 'codeMiss---%s' % e
        time.sleep(3)
        code = False
    return code


#把验证码图片下载下来
def save_img(imgURL,filename):
    # 下载图片，并保存到文件夹中
    try:
        urllib.urlretrieve(imgURL, filename=filename)

    except IOError as e:
        print '文件操作失败', e
    except Exception as e:
        print 'download fail*****%s'%e


#评价描述评分
def evaluationScoreURL(itemId,spuId,sellerId):
    evaluationScoresURL = 'https://dsr-rate.tmall.com/list_dsr_info.htm?itemId=' + str(itemId) + '&spuId=' + str(spuId) + '&sellerId=' + str(sellerId)

    request = urllib2.Request(url=evaluationScoresURL, headers=headers)
    # 获得回送的数据
    response = urllib2.urlopen(request)

    result = response.read()
    comments = '.*\((.*?)\)'

    apiData = re.findall(comments, result, re.S)[0]

    datas = json.loads(apiData)
    return datas['dsr']['gradeAvg']

#全部评价数据源
def commentContent(itemId,spuId,sellerId,currentPage):
    commentURL = 'https://rate.tmall.com/list_detail_rate.htm?itemId=' + str(itemId) + '&spuId=' + str(spuId) + '&sellerId=' + str(sellerId) + '&order=1&currentPage=' + currentPage + '&append=0&content=1&tagId=&posi=&picture=&needFold=0'
    print 'URL---%s',commentURL
    commentResult = getCommentResults(commentURL,'comResult')

    return commentResult


#TODO:XDF 由于在请求评价数据源时，会出现需要登录，返回内容则是{"rgv587_flag":"sm","url":"https://sec.taobao.com/query.htm?action=Que...}(具体自己打印)，所以我们得先登录
def commentLogin(result):
    print '需要登录淘宝'
    commentResult = json.loads(result)

    # TODO:XDF Chrome欲歌浏览器
    # options = webdriver.ChromeOptions()
    #
    # # 设置中文
    # options.add_argument('lang=zh_CN.UTF-8')
    # # prefs = {"profile.managed_default_content_settings.images": 2}
    # # options.add_experimental_option("prefs", prefs)  # TODO:XDF 禁止加载图片
    # # 更换头部
    # options.add_argument(
    #     'user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.101 Safari/537.36"')
    # driver = webdriver.Chrome(chrome_options=options,
    #                           executable_path=r'/Users/zhuoqin/Desktop/Python/SeleniumDemo/chromedriver')


    # TODO:XDF phantomjs无头浏览器
    dcap = dict(DesiredCapabilities.PHANTOMJS)
    dcap["phantomjs.page.settings.userAgent"] = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.101 Safari/537.36")  # 设置user-agent请求头
    dcap["phantomjs.page.settings.loadImages"] = False  # 禁止加载图片

    service_args = []
    service_args.append('--load-images=no')  ##关闭图片加载
    service_args.append('--disk-cache=yes')  ##开启缓存
    service_args.append('--ignore-ssl-errors=true')  ##忽略https错误

    # driver = webdriver.PhantomJS(executable_path=r'/usr/bin/phantomjs',service_args=service_args, desired_capabilities=dcap) #TODO:XDF 针对Linux

    driver = webdriver.PhantomJS(executable_path=r'/Users/zhuoqin/Desktop/Python/SeleniumDemo/phantomjs',desired_capabilities=dcap)  # TODO:XDF 针对本地调试

    driver.implicitly_wait(30)
    driver.set_page_load_timeout(30)

    wait = WebDriverWait(driver, 200, 0.5)  # 表示给browser浏览器一个10秒的加载时间

    driver.get(commentResult['url'])

    try:
        wait.until(EC.presence_of_element_located((By.ID, 'J_RegisterLink1')))  # 显性等待
        time.sleep(random.uniform(3, 6))
    except Exception as e:
        print '显性未加载成功---%s' % e
    driver.find_element_by_name("TPL_username").clear()
    driver.find_element_by_name("TPL_username").send_keys("13672456277")
    time.sleep(random.uniform(3,5))
    driver.find_element_by_name("TPL_password").clear()
    driver.find_element_by_name("TPL_password").send_keys("248552ZZN")
    time.sleep(random.uniform(3,5))
    if codeSEL(driver) == True:
        dragger = driver.find_element_by_class_name("nc_bg")

        action = ActionChains(driver)
        action.click_and_hold(dragger).perform()  # 鼠标左键按下不放
        print '456'
        for index in range(200):
            try:
                action.move_by_offset(2, 0).perform()  # 平行移动鼠标
            except UnexpectedAlertPresentException:
                break
            action.reset_actions()
            # time.sleep(random.uniform(0.01,0.05))  # 等待停顿时间
            time.sleep(random.randint(10,50)/100)

        # 打印警告框提示
        action.release().perform()

    time.sleep(1.5)

    driver.find_element_by_xpath('//*[@id="J_SubmitStatic"]').click()

    print '登录成功'
    driver.close()
    driver.quit()

def codeSEL(driver):
    try:
        driver.find_element_by_xpath('//*[@id="nc_1_n1z"]')
        codeTrue = True
    except Exception as e:
        print 'error--%s'%e
        codeTrue = False
    return codeTrue


#获取最后一页
def getLastPage(itemId,spuId,sellerId):
    # import sys
    # reload(sys)
    # sys.setdefaultencoding('gbk')
    commentURL = 'https://rate.tmall.com/list_detail_rate.htm?itemId='+str(itemId)+'&spuId='+spuId+'&sellerId='+sellerId+'&order=1&append=0&content=1&tagId=&posi=&picture=&needFold=0'

    commentResult = getCommentResults(commentURL,'lastPage')

    print 'lastPage--%s'%commentResult['rateDetail']['paginator']['lastPage']

    lastPage = commentResult['rateDetail']['paginator']['lastPage']
    return lastPage

#TODO:XDF 数据源抽取
def getCommentResults(commentURL,getNO):
    i = 0
    while True:
        if getNO == 'comResult':
            time.sleep(random.randint(4,10)) #这里是间隔请求时间随机数，避免被认为是程序执行

        req = urllib2.Request(commentURL)  # req表示向服务器发送请求#
        response = urllib2.urlopen(req)  # response表示通过调用urlopen并传入req返回响应 response#
        result = response.read()  # 用read解析获得的HTML文件#

        """
            这里要特别注意了，如果单纯用try内这种解码方式可能会报错：UnicodeDecodeError: 'gbk' codec can't decode bytes in position 6681-6682: illegal multibyte sequence ，很明显是编码问题
            在 commentData = '{' + result + '}'.decode(encoding='utf-8') 如果将.decode(encoding='utf-8') 删除，也可以显示数据，但是数据源中会出现乱码
            经过本人不断尝试，用except中的编码方式（其实只用except中的方法就可以了，但担心后面会出现问题，所以先保留）就可以解决编码问题了
            如果想看实际效果，可以请求以下URL获取数据源
            https://rate.tmall.com/list_detail_rate.htm?itemId=527123591448&spuId=509103357&sellerId=143584903&order=1&currentPage=37&append=0&content=1&tagId=&posi=&picture=&needFold=0
        """
        try:
            import sys
            reload(sys)
            sys.setdefaultencoding('gbk')
            commentData = '{' + result + '}'.decode(encoding='utf-8')
            print '第一种编码格式'
        except Exception as e:
            print 'codeError--%s'%e
            commentData = '{' + result + '}'
            # mychar = chardet.detect(commentData)
            # print '编码格式---%s'%mychar
            # tmallComment = mychar['encoding']
            # if tmallComment == 'utf-8' or tmallComment == 'UTF-8':
            #     commentData = commentData.decode('utf-8', 'ignore').encode('utf-8')  # ignore 忽略非法字符
            # else:
            #     commentData = commentData.decode('gb2312', 'ignore').encode('utf-8')
            commentData = settingNameCode(commentData)

        if 'https://sec.taobao.com/' in commentData:
            # commentLogin(result)
            print 'enter----login'
            time.sleep(random.uniform(3,6))
            if i==20:
                commentResult = {}
                break
            i += 1
        else:
            commentResult = json.loads(commentData)
            break
    return commentResult


#获取所有评论内容并保存到mongodb
def getAllCommentData(CommentData,commentItemID,shopName,itemId,title,TreasureLink,categoryName,itemName,EvaluationScores,ItemID):
    import sys
    reload(sys)
    sys.setdefaultencoding('utf-8')
    mychar = chardet.detect(itemName)
    print '编码格式---%s' % mychar
    for i in range(0, len(CommentData)):
        displayUserNick = CommentData[i]['displayUserNick']
        rateContent = CommentData[i]['rateContent']
        sellerId = CommentData[i]['sellerId']
        auctionSku = CommentData[i]['auctionSku']
        cmsSource = CommentData[i]['cmsSource']
        pics = CommentData[i]['pics']
        RateDate = CommentData[i]['rateDate']
        if len(CommentData[i]['appendComment']):
            IsAppend = 1
            appendCommentTime = CommentData[i]['appendComment']['commentTime']

            appendCommentTime = datetime.datetime.strptime(appendCommentTime, '%Y-%m-%d %H:%M:%S')

            appendContent = CommentData[i]['appendComment']['content']
            appendDifferDays = CommentData[i]['appendComment']['days'] #追评相差天数
            appendPics = CommentData[i]['appendComment']['pics']
            AppendImgURL = AppendImgServiceURL(appendPics)
        else:
            IsAppend = 0
            appendCommentTime = ''
            appendContent = ''
            appendDifferDays = ''
            # appendPics = ''
            AppendImgURL = ''



        allCommentContent = {
            # 'itemID': commentItemID,
            'TreasureID': itemId,
            'TreasureName': title,
            'displayUserNick': displayUserNick,
            'rateContent': rateContent,
            # 'sellerId': sellerId,
            'auctionSku': auctionSku,
            # 'cmsSource': cmsSource,
            'ImgServiceURL': ImgServiceURL(pics),
            'RateDate': datetime.datetime.strptime(RateDate, '%Y-%m-%d %H:%M:%S'),
            'IsAppend': IsAppend,
            'appendCommentTime': appendCommentTime,
            'appendContent': appendContent,
            'appendDifferDays': appendDifferDays,
            'appendPics': AppendImgURL,
            'ShopName':shopName,
            'Category_Name':settingNameCode(categoryName),
            'TreasureLink':TreasureLink,
            'ItemName':settingNameCode(itemName),
            'EvaluationScores':EvaluationScores,
            'ItemID':ItemID
        }

        saveCommentContent(allCommentContent)

#评论图片处理
def ImgServiceURL(pics):
    imageServer = []
    if len(pics):
        for i in range(0, len(pics)):
            imageServer.append('http:' + pics[i])

        ImageURL = ','.join(imageServer)
        return ImageURL
    return ' '


# 评论图片处理
def AppendImgServiceURL(appendPics):
    appendImageServer = []
    if len(appendPics):
        for i in range(0, len(appendPics)):
            appendImageServer.append('http:' + appendPics[i])

        AppendImageURL = ','.join(appendImageServer)
        return AppendImageURL
    return ' '



"""
    在爬虫中，也许会出现多种编码格式，就像KOI8-R（这也是我第一次见），如果不设置一下，会报如下错误
    编码格式---{'confidence': 0.7313997367253507, 'language': 'Russian', 'encoding': 'KOI8-R'}
                {'confidence': 0.25598990785387277, 'language': 'Russian', 'encoding': 'IBM855'}
                {'confidence': 0.73, 'language': '', 'encoding': 'ISO-8859-1'}
                {'confidence': 0.3391494065054961, 'language': 'Greek', 'encoding': 'ISO-8859-7'}
            save_Error...strings in documents must be valid UTF-8: '\xcc\xa9\xc9\xbd\xcf\xb5\xc1\xd0'
            {'confidence': 0.0, 'language': None, 'encoding': None}
            {'confidence': 0.73, 'language': '', 'encoding': 'Windows-1252'}
            {'confidence': 0.4626272726179244, 'language': 'Thai', 'encoding': 'TIS-620'}
            save_Error...strings in documents must be valid UTF-8: 'CQ\xca\xe9\xd7\xc0'
            
"""
def settingNameCode(itemName):
    import sys
    reload(sys)
    sys.setdefaultencoding('utf-8')
    mychar = chardet.detect(itemName)
    nameCode = mychar['encoding']
    nameLanguage = mychar['language']
    if nameCode == 'KOI8-R' or nameLanguage== 'Russian' or nameCode == 'ISO-8859-1' or nameCode == 'ISO-8859-7' or nameLanguage== 'Thai' or nameCode==None:
        Name = itemName.decode('gb18030').encode('utf-8')
    elif nameCode == 'utf-8' or nameCode == 'UTF-8':
        Name = itemName.decode('utf-8', 'ignore').encode('utf-8')
    elif nameCode == 'GB2312' or nameCode == 'gb2312':
        Name = itemName.decode('gb2312', 'ignore').encode('utf-8')
    elif nameCode == 'Windows-1252':
        Name = itemName.decode('Windows-1252').encode('utf-8')
    else:
        Name = itemName
    return Name

def saveCommentContent(allCommentContent):
    # print '保存数据为--%s'%allCommentContent
    try:
        if commentContentTB.insert(allCommentContent):
            print ('commentContentTB saveSuccess')
    except Exception as e:
        print ('save_Error...%s'%e)


if __name__ == '__main__':
    commentSpider()
    # ceShiHTML()



































