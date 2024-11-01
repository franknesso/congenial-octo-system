import requests
import streamlit as st

API_KEY = '21027f31-6334-4abe-98c0-7bede6caf0c5'

if 'labr_token_balance' not in st.session_state:
    st.session_state['labr_token_balance'] = None
    st.session_state['wtrx_token_balance'] = None
    st.session_state['wtrx_price_in_usd'] = None
    st.session_state['latest_labr_price'] = None

@st.cache_data(ttl=60)
def fetch_data():
    try:
        response = requests.get(
            f'https://apilist.tronscanapi.com/api/account/tokens?address=TV2R7Hh1p3tbrJXhLJcYwMg3LZ7PNxRZGN&limit=20&TRON-PRO-API-KEY={API_KEY}'
        )

        if response.status_code != 200:
            st.error(f"Ошибка: не удалось получить данные. Код состояния: {response.status_code}")
            return

        response_in_json = response.json()

        if 'data' not in response_in_json:
            st.error("Ошибка: ключ 'data' не найден в ответе API.")
            return

        labr_token_balance = next((token['quantity'] for token in response_in_json['data'] if token['tokenAbbr'] == 'LABR'), None)
        wtrx_token_balance = next((token['quantity'] for token in response_in_json['data'] if token['tokenAbbr'] == 'WTRX'), None)

        response = requests.get(
            f'https://apilist.tronscanapi.com/api/token_trc20?contract=TNUC9Qb1rRpS5CbWLmNMxXBjyFoydXjWFR&showAll=1&limit=1&TRON-PRO-API-KEY={API_KEY}'
        )

        if response.status_code != 200:
            st.error(f"Ошибка: не удалось получить цену WTRX. Код состояния: {response.status_code}")
            return

        response_in_json = response.json()

        if 'trc20_tokens' not in response_in_json or not response_in_json['trc20_tokens']:
            st.error("Ошибка: данные 'trc20_tokens' не найдены в ответе API.")
            return

        wtrx_price_in_usd = response_in_json['trc20_tokens'][0]['market_info'].get('priceInUsd', None)

        if labr_token_balance and wtrx_token_balance and wtrx_price_in_usd:
            st.session_state['labr_token_balance'] = labr_token_balance
            st.session_state['wtrx_token_balance'] = wtrx_token_balance
            st.session_state['wtrx_price_in_usd'] = wtrx_price_in_usd
            st.session_state['latest_labr_price'] = wtrx_token_balance / labr_token_balance * wtrx_price_in_usd
        else:
            st.error("Ошибка: не удалось получить все необходимые данные.")
    except Exception as e:
        st.error(f'Ошибка при загрузке данных: {e}')

def calculate_slippage(token_x_balance: int, token_y_balance: int, delta_x: int, delta_y: int) -> float:
    return (delta_x / delta_y) - (token_x_balance / token_y_balance)

def calculate_price_after_buying(token_x_balance: int, token_y_balance: int, delta_x: int) -> float:
    delta_y = (delta_x * token_y_balance) / (token_x_balance + delta_x)
    slippage = calculate_slippage(token_x_balance, token_y_balance, delta_x, delta_y)
    new_token_x_balance = token_x_balance + delta_x
    new_token_y_balance = token_y_balance - delta_y
    st.write(f'Обновленные балансы пула ликвидности: {new_token_x_balance} TRX | {new_token_y_balance} LABR')
    return (new_token_x_balance / new_token_y_balance) * (1 + slippage)

def calculate_price_after_selling(token_x_balance: int, token_y_balance: int, delta_y: int) -> float:
    delta_x = (delta_y * token_x_balance) / (token_y_balance + delta_y)
    slippage = calculate_slippage(token_x_balance, token_y_balance, delta_x, delta_y)
    new_token_x_balance = token_x_balance - delta_x
    new_token_y_balance = token_y_balance + delta_y
    st.write(f'Обновленные балансы пула ликвидности: {new_token_x_balance} TRX | {new_token_y_balance} LABR')
    return (new_token_x_balance / new_token_y_balance) * (1 - slippage)

def main():
    st.title("LABR Token Price Calculator")
    
    fetch_data()
    print(st.session_state['latest_labr_price'], st.session_state['labr_token_balance'], st.session_state['wtrx_token_balance'], st.session_state['wtrx_price_in_usd'])

    if not all([st.session_state['labr_token_balance'], st.session_state['wtrx_token_balance'], st.session_state['wtrx_price_in_usd'], st.session_state['latest_labr_price']]):
        st.error("Данные временно недоступны. Попробуйте позже.")
        return

    st.write(f'**Current LABR price:** {st.session_state["latest_labr_price"]:.6f} USD')

    tx_type_choice = st.selectbox('Выберите тип транзакции', ['Продажа', 'Покупка'])

    if tx_type_choice == 'Продажа':
        labr_amount = st.number_input('Введите количество LABR:', min_value=1, step=1)
        if st.button('Рассчитать цену после продажи'):
            new_labr_price = calculate_price_after_selling(st.session_state['wtrx_token_balance'], st.session_state['labr_token_balance'], labr_amount) * st.session_state['wtrx_price_in_usd']
            st.write(f'**Цена после продажи:** {new_labr_price:.6f} USD')
            st.write(f'Изменение цены: {(new_labr_price - st.session_state["latest_labr_price"]):.6f} USD ({((new_labr_price - st.session_state["latest_labr_price"]) / st.session_state["latest_labr_price"] * 100):.1f}%)')

    elif tx_type_choice == 'Покупка':
        currency_choice = st.selectbox('Выберите валюту', ['USD', 'TRX'])
        if currency_choice == 'USD':
            amount_in_usd = st.number_input('Введите сумму в USD:', min_value=1, step=1)
            amount_in_wtrx = amount_in_usd / st.session_state['wtrx_price_in_usd']
        else:
            amount_in_wtrx = st.number_input('Введите сумму в TRX:', min_value=1, step=1)

        if st.button('Рассчитать цену после покупки'):
            new_labr_price = calculate_price_after_buying(st.session_state['wtrx_token_balance'], st.session_state['labr_token_balance'], amount_in_wtrx) * st.session_state['wtrx_price_in_usd']
            st.write(f'**Цена после покупки:** {new_labr_price:.6f} USD')
            st.write(f'Изменение цены: {(new_labr_price - st.session_state["latest_labr_price"]):.6f} USD ({((new_labr_price - st.session_state["latest_labr_price"]) / st.session_state["latest_labr_price"] * 100):.1f}%)')

if __name__ == '__main__':
    main()
