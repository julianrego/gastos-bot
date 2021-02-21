from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import logging
import os
import pandas as pd

logging.basicConfig(filename='log-bot-gastos.log',
                    filemode='a',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

with open('token.txt', 'r') as f:
    __TOKEN__ = f.read()

PORT = int(os.environ.get('PORT', 5000))

def represents_int(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False

def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Me gusta jugar rol, tomar birra y comer papitas")

def process_messages(update, context):
    if not (update.edited_message is None):
        #Si se edito un mensaje que ya habia sido enviado en vez de enviar un gasto con un mensaje
        
        #chequeo formato
        if not (':' in update.edited_message.text):
            update.edited_message.reply_text('La edicion del mensaje no fue añadida a los gastos')
        elif '\n' in update.edited_message.text:
            update.edited_message.reply_text('La edicion del mensaje no fue añadida a los gastos. Los gastos tienen que ser añadidos de a uno')
        else:

            parts = update.edited_message.text.split(':')
            if len(parts)!=2:
                update.edited_message.reply_text('Este mensaje no fue añadido a los gastos. El gasto tiene que tener el formato \"concepto:monto\"')
            elif not represents_int(parts[1]):
                update.edited_message.reply_text('Este mensaje no fue añadido a los gastos. El gasto tiene que tener el formato \"concepto:monto\" y el monto debe ser un numero entero')
            else:
                concepto_nuevo = parts[0].strip().lower()
                monto_nuevo = int(parts[1].strip())
                
                filename = f'gastos_{update.edited_message.chat_id}.csv'

                gastos = pd.read_csv(filename)

                fila_a_modificar = (
                    (gastos['datetime']==update.edited_message.date.strftime('%Y-%m-%d %H:%M:%S'))
                    & (gastos['usuario'] == update.edited_message.from_user.full_name)
                )

                if any(fila_a_modificar):
                    gastos.loc[fila_a_modificar, ['concepto', 'monto']] = [concepto_nuevo, monto_nuevo]
                else:
                    gastos = gastos.append({
                        'datetime':update.edited_message.date.strftime('%Y-%m-%d %H:%M:%S'),
                        'usuario':update.edited_message.from_user.full_name,
                        'concepto':concepto_nuevo,
                        'monto':monto_nuevo
                    },
                    ignore_index=True)

                gastos.to_csv(filename, index=False)
                update.edited_message.reply_text('Gasto editado')
    else: 
        #si es un mensaje que o fue editado, o sea que es nuevo
        if not (':' in update.message.text):
            update.message.reply_text('Este mensaje no fue añadido a los gastos')
        elif '\n' in update.message.text:
            update.message.reply_text('Este mensaje no fue añadido a los gastos. Los gastos tienen que ser añadidos de a uno')
        else:
            parts = update.message.text.split(':')
            if len(parts)!=2:
                update.message.reply_text('Este mensaje no fue añadido a los gastos. El gasto tiene que tener el formato \"concepto:monto\"')
            elif not represents_int(parts[1]):
                update.message.reply_text('Este mensaje no fue añadido a los gastos. El gasto tiene que tener el formato \"concepto:monto\" y el monto debe ser un numero entero')
            else:
                concepto = parts[0].strip().lower()
                monto = int(parts[1].strip())
                
                filename = f'gastos_{update.message.chat_id}.csv'
                if os.path.exists(filename):
                    gastos = pd.read_csv(filename)
                else:
                    gastos = pd.DataFrame(columns=['datetime','usuario', 'concepto', 'monto'])
                
                gastos = gastos.append({
                    'datetime':update.message.date.strftime('%Y-%m-%d %H:%M:%S'),
                    'usuario':update.message.from_user.full_name,
                    'concepto':concepto,
                    'monto':monto
                },
                ignore_index=True)

                gastos.to_csv(filename, index=False)
                update.message.reply_text('Gasto añadido')

def get_balance(update, context):

    filename = f'gastos_{update.message.chat_id}.csv'

    df_gastos = pd.read_csv(filename)

    gastos = df_gastos.groupby('usuario')['monto'].sum().to_dict()

    if len(df_gastos)==0:
        context.bot.send_message(chat_id=update.message.chat_id, text='No hay gastos nuevos desde la ultima vez saldada')

    else:
        mensaje_1 = [f'{usuario} gastó {monto}' for usuario, monto in gastos.items()]
        mensaje_1 = '\n'.join(mensaje_1)

        cant_usuarios = len(df_gastos['usuario'].unique())
        gasto_total = df_gastos['monto'].sum()
        promedio = gasto_total / cant_usuarios

        mensaje_2 = [f"{usuario} puso {abs(monto-promedio)} de {'menos' if monto-promedio<0 else 'mas'}" for usuario, monto in gastos.items()]
        mensaje_2 = '\n'.join(mensaje_2)

        mensaje = f"En total se gasto {gasto_total}\n \n" + mensaje_1 + "\n \n" + mensaje_2

        context.bot.send_message(chat_id=update.message.chat_id, text=mensaje)

def volver_a_cero(update, context):

    filename = f'gastos_{update.message.chat_id}.csv'

    pd.DataFrame(columns=['datetime','usuario', 'concepto', 'monto']).to_csv(filename, index=False)

    context.bot.send_message(chat_id=update.message.chat_id, text="Saldado. Cuenta reiniciada a cero")

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

updater = Updater(token=__TOKEN__, use_context=True)
dispatcher = updater.dispatcher

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

echo_handler = MessageHandler(Filters.text & (~Filters.command), process_messages)
dispatcher.add_handler(echo_handler)

balance_expenses = CommandHandler('balance', get_balance)
dispatcher.add_handler(balance_expenses)

saldar = CommandHandler('saldar', volver_a_cero)
dispatcher.add_handler(saldar)

dispatcher.add_error_handler(error)

updater.start_webhook(listen="0.0.0.0",
                          port=int(PORT),
                          url_path=__OKEN__)
updater.bot.setWebhook('https://gastos-hogar-bot.herokuapp.com/' + __TOKEN__)

updater.idle()

updater.start_polling()