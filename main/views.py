from functools import wraps
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect
import requests
import json
from integration_utils.bitrix24.bitrix_user_auth.main_auth import main_auth
import bitrix_app.urls
from django.core.cache import cache
from django.conf import settings
from integration_utils.bitrix24.bitrix_token import BitrixToken
from django.core.signing import Signer
import qrcode
import io
import base64
import qrcode.image.svg
from django.core import signing
from django.core.signing import BadSignature
from django.http import Http404
import random
from datetime import datetime, timedelta
from django.http import JsonResponse

def check_calls(id,call_counts):
    if id in call_counts:
        count = call_counts[id]
    else:
        count = 0
    return count


def create_call_counts(calls):
    call_counts = {}
    for call in calls:
        employee_id = call['PORTAL_USER_ID']

        if employee_id in call_counts:
            call_counts[employee_id] += 1  # Если ID уже есть в словаре — увеличиваем счётчик

        else:
            call_counts[employee_id] = 1  # Если нет — добавляем и ставим 1
    return call_counts

def add_head(department,user_dict,heads,user):
    head_id = str(department['UF_HEAD'])
    head = user_dict.get(head_id)
    full_name = f"{head['NAME']} {head['LAST_NAME']}"
    if full_name not in heads and user['ID'] != head['ID']:  # Проверка на дубликаты и что не руководитель себе
        heads.append(full_name)
    return heads
@main_auth(on_start=True, set_cookie=True)
def start(request):
    context = {
        'user_first_name': request.bitrix_user.first_name,
        'user_last_name': request.bitrix_user.last_name,
    }

    return render(request, 'main/index.html', context)
@main_auth(on_cookies= True)
def index(request):
    print(dir(request))
    print(type(request.bitrix_user))

    context = {
        'user_first_name': request.bitrix_user.first_name,
        'user_last_name': request.bitrix_user.last_name,
    }

    return render(request, 'main/index.html', context)

@main_auth(on_cookies= True)
def last_active_deals(request):
    auth_token = request.bitrix_user_token.auth_token
    print('auth_token:', auth_token)
    print(request.bitrix_user_token.domain)
    print(settings.WEBHOOK_URL + 'crm.product.get.json')
    deals = []
    error = None
    deals = request.bitrix_user_token.call_api_method(
        api_method='crm.deal.list',
        params={
            'auth': auth_token,
            'order': {'DATE_CREATE': 'DESC'},
            'filter': {
                '!@STAGE_ID': ['WON', 'LOSE', 'APOLOGY']
            },
            'select': ['ID','STAGE_ID', 'TITLE', 'DATE_CREATE', 'OPPORTUNITY', 'UF_CRM_1754146731437']
        }
    )['result'][:10]

    for deal in deals:
        if deal['UF_CRM_1754146731437']=='1':
            deal['UF_CRM_1754146731437'] = 'Да'
        else:
            deal['UF_CRM_1754146731437'] = 'Нет'

    return render(request, 'main/last_active_deals.html', {
        'deals': deals,
        'error': error
    })


@main_auth(on_cookies= True)
def add_deal(request):
    if request.method == 'POST':
        auth_token = request.bitrix_user_token.auth_token
        loyal_value='0'
        if request.POST.get('loyal')=='on':
            loyal_value='1'
        
        request.bitrix_user_token.call_api_method(
            api_method='crm.deal.add',
            params={
                'auth': auth_token,
                'fields': {
                    'TITLE': request.POST.get('title'),
                    'STAGE_ID': request.POST.get('stage_id'),
                    'OPPORTUNITY': request.POST.get('amount'),
                    'UF_CRM_1754146731437': loyal_value,
                }
            }
        )
        return redirect('main:last_active_deals')

    return render(request, 'main/add_deal.html')


@main_auth(on_cookies= True)
def qr_generate(request):
    product = None
    image_url = None
    qr_image = None

    if request.method == 'POST':

        auth_token = request.bitrix_user_token.auth_token
        product_id = request.POST.get('id')
        product = cache.get(f'product_{product_id}')
        if not product:
            product = request.bitrix_user_token.call_api_method(
                api_method='crm.product.get',
                params={
                    'auth': auth_token,
                    'id': request.POST.get('id'),
                    }
            )
            cache.set(f'product_{product_id}', product, timeout=3600)

        image_url = 'https://'+request.bitrix_user_token.domain+product['result']['PROPERTY_45'][0]['value']['downloadUrl']

        signer = Signer()
        signed_id = signer.sign(product_id)

        product_url_qr = f"http://localhost:8000/product/{signed_id}/"

        qr_image = qrcode.make(product_url_qr)
        buffer = io.BytesIO()
        qr_image.save(buffer, format="PNG")
        qr_image_bytes = buffer.getvalue()
        buffer.close()
        qr_image_decode = base64.b64encode(qr_image_bytes).decode('utf-8')

        return render(request, 'main/qr_generate.html', {
            'product': product['result'],
            'image_url': image_url,
            'qr_image': qr_image_decode, # Сгенерированный qr-код
            'product_url_qr': product_url_qr,  # Сгенерированная ссылка
            })

    return render(request, 'main/qr_generate.html')


def product_detail(request, signed_id):
    try:
        signer = signing.Signer()
        product_id = signer.unsign(signed_id)  # Достаём исходный ID
    except (signing.BadSignature, signing.SignatureExpired):
        raise Http404("Неверная ссылка или срок действия истёк")  # Обработка ошибки подписи

    webhook_token = BitrixToken(
        domain= settings.APP_SETTINGS.portal_domain,
        web_hook_auth=settings.WEBHOOK_AUTH,
    )
    print('webhook:', webhook_token)
    product = webhook_token.call_api_method(
        api_method='crm.product.get',
        params={
            'id': product_id,
        },
    )
    image = webhook_token.call_api_method(
        api_method='catalog.productImage.list',
        params={
            'productId': product_id,
            'select': ['detailUrl']
        },
    )

    return render(request, 'main/product_detail.html',{
            'product': product['result'],
            'image_url': image['result']['productImages'][0]['detailUrl'],
            })


@main_auth(on_cookies= True)
def active_users_list(request):
    auth_token = request.bitrix_user_token.auth_token

    users = request.bitrix_user_token.call_api_method(
        api_method='user.get',
        params={
            'auth': auth_token,
            'ACTIVE': True,
            'SELECT': ['ID', 'NAME', 'LAST_NAME', 'UF_DEPARTMENT', 'WORK_POSITION', 'EMAIL']
        }
    )['result']

    departments = request.bitrix_user_token.call_api_method(
        api_method='department.get',
        params={
            'auth': auth_token,
        }
    )['result']

    # Создадим словарь для быстрого поиска департаментов и юзеров по id
    department_dict = {dept['ID']: dept for dept in departments}
    user_dict = {dept['ID']: dept for dept in users}
    calls = request.bitrix_user_token.call_list_method( 'voximplant.statistic.get',
        {
            'FILTER': {
                '>=CALL_START_DATE': (datetime.now() - timedelta(days=1)).isoformat(),
                'CALL_TYPE': '1',
                '>CALL_DURATION': 60  # Только звонки >1 минуты
            }
        }
    )
    print('звонков', calls)
    call_counts = create_call_counts(calls)

    for user in users:
        user['HEAD'] = ''
        heads = []
        user['COUNT_CALLS'] = check_calls(user['ID'], call_counts)
        department_ids = user["UF_DEPARTMENT"]
        department = department_dict.get(str(department_ids[0]))
        user['NAME_DEPARTMENT'] = department['NAME']
        add_head(department, user_dict, heads, user)
        if department.get('PARENT') is not None:
            head_dep = department['PARENT']
            while department.get('PARENT') is not None:
                department = department_dict.get(department['PARENT'])
                add_head(department, user_dict, heads, user)
        if heads:
            user['HEAD'] = ', '.join(heads)

    return render(request, 'main/active_users_list.html', {
        'users': users,
    })


@main_auth(on_cookies=True)
def calls_generate(request):
    auth_token = request.bitrix_user_token.auth_token
    users = request.bitrix_user_token.call_api_method(
        api_method='user.get',
        params={
            'auth': auth_token,
            'ACTIVE': True,
            'SELECT': ['ID']
        }
    )['result']
    for i in range(5):
        random_user = random.choice(users)  # Случайный user из списка
        random_id = random_user['ID']  # Достаём его ID
        call = request.bitrix_user_token.call_api_method(
            api_method='telephony.externalcall.register',
            params={
                'USER_ID': random_id,
                'PHONE_NUMBER': '+7' + ''.join([str(random.randint(0, 9)) for _ in range(10)]),
                'TYPE': 1,
                'SHOW': 0,
            }
        )['result']
        calls = request.bitrix_user_token.call_api_method(
            api_method='telephony.externalcall.finish',
            params={
                'CALL_ID': call['CALL_ID'],
                'USER_ID': random_id,
                'DURATION': '70',
            }
        )

    return JsonResponse({"status": "success"})

