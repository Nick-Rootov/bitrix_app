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

