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
import time
from django.http import JsonResponse, HttpResponse
from services.exports.exporter_factory import ExporterFactory
import os
from services.imports.importer_factory import ImporterFactory
from django.contrib import messages


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


def geocode_address(address):
    base_url = "https://geocode-maps.yandex.ru/1.x/"
    print(settings.YANDEX_API_KEY)
    params = {
        "geocode": address,
        "apikey": settings.YANDEX_API_KEY,
        "format": "json",
    }

    try:
        response = requests.get(base_url, params=params)
        data = response.json()
        # Парсим координаты из ответа
        pos = data['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
        parts = pos.split()
        lat = float(parts[0])
        lon = float(parts[1])
        return {"lat": lat, "lon": lon}

    except (KeyError, IndexError):
        print(f"Ошибка геокодирования для адреса: {address}")
        return None
    except Exception as e:
        print(f"Ошибка запроса: {e}")
        return None

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
    print(users)
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

@main_auth(on_cookies=True)
def map(request):
    company = request.bitrix_user_token.call_api_method(
        api_method='crm.company.list',
        params={
            'SELECT': ['ID', 'TITLE']
        }
    )['result']

    address = request.bitrix_user_token.call_api_method(
        api_method='crm.address.list',
        params={
            'SELECT': ['ENTITY_ID', 'ADDRESS_2']
        }
    )['result']

    address_dict = {ad['ENTITY_ID']: ad['ADDRESS_2'] for ad in address}
    for comp in company:
        comp['ADDRESS'] = address_dict.get(comp['ID'], 'Адрес неизвестен')
        coords = geocode_address(comp['ADDRESS'])
        if coords:
            comp['COORDS'] = [coords['lon'], coords['lat']]
        else:
            comp['COORDS'] = None


    print(company)
    return render(request, 'main/map.html', {
        'company': company,
    })


@main_auth(on_cookies=True)
def export_data(request):
    if request.method == 'POST':
        format_type = request.POST.get('export_format', 'csv')  # По умолчанию CSV

        contacts = request.bitrix_user_token.call_api_method(
            api_method='crm.contact.list',
            params={
                'SELECT': ['ID', 'NAME', 'LAST_NAME', 'PHONE', 'EMAIL', 'COMPANY_ID']
            }
        )['result']
        departments = request.bitrix_user_token.call_api_method(
            api_method='crm.company.list',
            params={
                'SELECT': ['ID', 'TITLE'],
            }
        )['result']
        department_dict = {dept['ID']: dept for dept in departments}
        for contact in contacts:
            contact['PHONE'] = contact['PHONE'][0]['VALUE']
            contact['EMAIL'] = contact['EMAIL'][0]['VALUE']
            contact['COMPANY'] = department_dict.get(contact['COMPANY_ID'])['TITLE']
            contact.pop('ID', None)
            contact.pop('COMPANY_ID', None)
        print("data:", contacts)
        try:
            exporter = ExporterFactory.get_exporter(format_type)
            file_path = f"export.{format_type}"
            exporter.export(contacts, file_path)

            # Отправляем файл пользователю
            with open(file_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type=f"application/{format_type}")
                response['Content-Disposition'] = f'attachment; filename=export.{format_type}'
                return response

        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)

    return render(request, 'main/export_data.html')


@main_auth(on_cookies=True)
def import_data(request):
    if request.method == 'POST':
        uploaded_file = request.FILES['import_file']
        file_name, file_ext = os.path.splitext(uploaded_file.name)
        if file_ext not in ['.csv', '.xlsx']:
            return JsonResponse({'error': 'Неподдерживаемый формат файла'}, status=400)
        try:
            # Сохраняем временный файл
            temp_path = f"temp_import{file_ext}"
            with open(temp_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # Получаем нужный импортер
            importer = ImporterFactory.get_importer(file_ext)

            # Импортируем данные
            data_contacts = importer.import_data(temp_path)

            print('data_contacts', data_contacts)

            contacts = request.bitrix_user_token.call_api_method(
                api_method='crm.contact.list',
                params={
                    'SELECT': ['ID', 'NAME', 'LAST_NAME', 'PHONE', 'EMAIL', 'COMPANY_ID']
                }
            )['result']
            departments = request.bitrix_user_token.call_api_method(
                api_method='crm.company.list',
                params={
                    'SELECT': ['ID', 'TITLE'],
                }
            )['result']
            contacts_to_add = [] # Список пользователей для добавления
            contacts_dict = {} # Словарь существующих емейлов
            for contact in contacts:
                email = contact['EMAIL'][0]['VALUE']
                contact['EMAIL'] = email
                contacts_dict[email] =contact['ID']
            department_dict = {dept['TITLE']: dept['ID'] for dept in departments}

            for cont in data_contacts:
                email = cont['EMAIL']
                if email not in contacts_dict:
                    contacts_to_add.append(cont)  # Добавляем в список на вставку

            for cont in contacts_to_add:
                if department_dict.get(cont['COMPANY']) or cont['COMPANY'] is None:
                    dept_id = department_dict.get(cont['COMPANY'])
                else:
                    result = request.bitrix_user_token.call_api_method(
                        api_method='crm.company.add',
                        params={
                            'fields': {
                                'TITLE': cont['COMPANY'],
                            }
                        }
                    )
                    if 'error' in result:
                        print(f"Ошибка при создании компании: {result['error_description']}")
                        dept_id = None
                    # Если успешный ответ
                    elif 'result' in result:
                        dept_id = result['result']
                    else:
                        print("Неожиданный формат ответа от API:", result)
                        dept_id = None
                cont['COMPANY_ID'] = dept_id
                request.bitrix_user_token.call_api_method(
                    api_method='crm.contact.add',
                    params={
                        'fields': {
                            'NAME': cont['NAME'],
                            'LAST_NAME': cont['LAST_NAME'],
                            'COMPANY_ID': cont['COMPANY_ID'],
                            'PHONE': [{'VALUE': '+' + str(cont['PHONE'])}],
                            'EMAIL': [{'VALUE': cont['EMAIL']}],
                        }
                    }
                )
            #return JsonResponse({'status': 'success','data': imported_data})
            messages.success(request, 'Данные успешно импортированы!')
            return redirect('main:import_data')


        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'error': f"Ошибка импорта: {str(e)}"}, status=500)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    return render(request, 'main/import_data.html')
