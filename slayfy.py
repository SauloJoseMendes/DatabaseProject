##
## =============================================
## ============== Bases de Dados ===============
## ============== LEI  2022/2023 ===============
## =============================================

##
## Catarina Silva 2021216307
## Diogo Barbosa 2021234034
## Saulo José Mendes 2021235944

import flask
from flask import request
import logging
import psycopg2
import jwt
from datetime import date, timedelta
import time
import random
import datetime
from dateutil.relativedelta import relativedelta

app = flask.Flask(__name__)

StatusCodes = {
    'success': 200,
    'api_error': 400,
    'internal_error': 500
}


##########################################################
## DATABASE ACCESS
##########################################################

def db_connection():
    db = psycopg2.connect(
        user='aulaspl',
        password='aulaspl',
        host='127.0.0.1',
        port='5432',
        database='slayfy'
    )

    return db


##########################################################
## ENDPOINTS
##########################################################


@app.route('/')
def landing_page():
    return """Welcome to our music platform Slayfy created by three music admirers"""


#ENDPOINT PARA REGISTAR UM CONSUMIDOR OU UM USER
@app.route('/slayfy/slayfy_user', methods=['POST'])
def register_user():
    logger.info('POST /slayfy/slayfy_user')

    payload = flask.request.get_json()

    conn = db_connection()
    cur = conn.cursor()

    logger.debug(f'POST /slayfy/slayfy_user - payload: {payload}')

    token = request.headers.get('Authentication')  # ver se já há uma sessão iniciada

    # validar argumentos
    if 'username' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'username not in payload'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    if 'password' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'password not in payload'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    if 'mail' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'mail not in payload'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    if 'artist_permit' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'artist_permit not in payload'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    # se vamos inserir um consumidor
    if payload['artist_permit'] == 'False':

        # para registar um user, não pode haver nenhuma sessão iniciada
        if not token:
            statement1 = 'INSERT INTO slayfy_user (username, password, mail, admin_permit, artist_permit) VALUES (%s, %s, %s, %s, %s) RETURNING user_id'
            values1 = (payload['username'], payload['password'], payload['mail'], False, payload['artist_permit'])

            statement2 = 'INSERT INTO consumer VALUES (%s, %s::bigint)'

            try:
                cur.execute('LOCK TABLE slayfy_user IN SHARE MODE')  # não permitir modificações na tabela slayfy_user até terminarmos a transação
                cur.execute(statement1, values1)  # criar utilizador na base de dados principal

                id = cur.fetchone()[0]

                values2 = (False, id)  # todos os consumers começam sem plano premium
                cur.execute(statement2, values2)  # colocar o novo user na tabela de consumidores

                #create top10 playlist for consumer
                statement = 'INSERT INTO playlist(title, by_system, public, creation_date, consumer_slayfy_user_user_id) VALUES(%s, %s, %s, %s, %s)'
                values = ('Top 10 for ' + payload['username'], True, False, datetime.datetime.today(), id)
                cur.execute('LOCK TABLE playlist IN SHARE MODE')  # não permitir modificações na tabela playlist até terminarmos a transação
                cur.execute(statement, values)


                # commit the transaction
                conn.commit()
                response = {'status': StatusCodes['success'], 'results': f'Inserted consumer with id {id}'}

            except (Exception, psycopg2.DatabaseError) as error:
                logger.error(f'POST /slayfy/slayfy_user - error: {error}')
                response = {'status': StatusCodes['internal_error'], 'errors': str(error)}

                # an error occurred, rollback
                conn.rollback()

            finally:
                if conn is not None:
                    conn.close()

        else:  # se já há uma sessão autenticada
            response = {'status': StatusCodes['api_error'], 'results': 'There is already an active session!'}

        return flask.jsonify(response)


    # se vamos inserir um artista
    else:
        # são precisos argumentos adicionais que serão adicionados à tabela de artista
        if 'artistic_name' not in payload:
            response = {'status': StatusCodes['api_error'], 'results': 'artistic_name not in payload'}
            if conn is not None:
                conn.close()
            return flask.jsonify(response)

        if 'genre' not in payload:
            response = {'status': StatusCodes['api_error'], 'results': 'genre not in payload'}
            if conn is not None:
                conn.close()
            return flask.jsonify(response)

        #se não há ninguém autenticado
        if not token:
            response = {'status': StatusCodes['api_error'], 'results': 'An artist can only be created by an admin!'}

        else:
            #verificar se o user autenticado é um administrador
            secret_key = 'slayfy'
            info = jwt.decode(token, secret_key, algorithms=['HS256'])
            admin_permit = info['admin_permit']

            # se a sessão é de um administrador, prosseguir com a inserção do user
            if admin_permit:

                statement1 = 'INSERT INTO slayfy_user (username, password, mail, admin_permit, artist_permit) VALUES (%s, %s, %s, %s, %s) RETURNING user_id'
                values1 = (payload['username'], payload['password'], payload['mail'], False, payload['artist_permit'])

                statement2 = 'INSERT INTO artist VALUES (%s, %s, %s)'

                try:
                    cur.execute('LOCK TABLE slayfy_user IN SHARE MODE')  # não permitir modificações na tabela slayfy_user até terminarmos a transação
                    cur.execute(statement1, values1)  # criar utilizador na base de dados principal
                    id = cur.fetchone()[0]

                    values2 = (payload['artistic_name'], payload['genre'], id)
                    cur.execute(statement2, values2)  # colocar o novo user na tabela de artista

                    # commit the transaction
                    conn.commit()
                    response = {'status': StatusCodes['success'], 'results': f'Inserted artist with id {id}'}

                except (Exception, psycopg2.DatabaseError) as error:
                    logger.error(f'POST /slayfy/slayfy_user - error: {error}')
                    response = {'status': StatusCodes['internal_error'], 'errors': str(error)}

                    # an error occurred, rollback
                    conn.rollback()

                finally:
                    if conn is not None:
                        conn.close()

            # se não há um admin autenticado
            else:
                response = {'status': StatusCodes['api_error'], 'results': 'An artist can only be created by an admin!'}

        return flask.jsonify(response)


#ENDPOINT PARA AUTENTICAÇÃO DO USER
@app.route('/slayfy/slayfy_user/', methods=['PUT'])
def user_authentication():
    logger.info('PUT /slayfy/slayfy_user')

    payload = flask.request.get_json()

    conn = db_connection()
    cur = conn.cursor()

    logger.debug(f'PUT /slayfy/slayfy_user - payload: {payload}')

    token = request.headers.get('Authentication') #extrair autenticação

    if token:  # se o user já está autenticado
        response = {'status': StatusCodes['api_error'], 'results': 'There is already an active session!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    # validate arguments
    if 'username' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'username not in payload'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    if 'password' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'password not in payload'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)


    statement = 'SELECT * from slayfy_user WHERE username like %s and password like %s'
    values = (payload['username'], payload['password'])

    try:
        cur.execute(statement, values)  # procurar credenciais na tabela principal de utilizadores

        #se as credenciais não foram encontradas
        if cur.rowcount == 0:
            conn.rollback()
            response = {'status': StatusCodes['api_error'], 'results': 'Username ou password errados'}

        else:
            user = cur.fetchone()
            id = user[0]
            username = user[3]
            admin_permit = user[4]
            artist_permit = user[5]

            #se o user a fazer login é um consumidor, vamos fazer refresh do seu estado de premium
            #ao verificar se a sua subscrição mais recente já expirou
            if(admin_permit is False and artist_permit is False):
                statement_verify = """  SELECT (MAX(subs_end) > CURRENT_TIMESTAMP) AS is_ahead
                                        FROM subscription
                                        WHERE consumer_slayfy_user_user_id = %s;"""
                cur.execute(statement_verify, (id,))

                is_premium = cur.fetchone()[0]

                #se o user não tinha qualquer subscrição
                if is_premium is None:
                    is_premium = False

                statement_update = """  UPDATE consumer
                                        SET is_premium = %s
                                        WHERE slayfy_user_user_id = %s;"""

                cur.execute(statement_update, (is_premium, id)) #atualizar estado premium do consumidor

            #obter token de autenticação associado ao user
            statement2 = 'SELECT token from authentication WHERE slayfy_user_user_id = %s'
            cur.execute(statement2, (id,))
            #se o utilizador ainda não tem um token de autenticação, é preciso criar um
            if cur.rowcount == 0:
                #guardar informação pertinente no token de autenticação, como o id, username e permissões
                content = {
                    'id': id,
                    'username': username,
                    'admin_permit': admin_permit,
                    'artist_permit': artist_permit,
                }

                secret_key = 'slayfy'  # chave para encriptação do token

                token = jwt.encode(content, secret_key, algorithm='HS256')  # criação do token

                #inserir token na tabela de autenticação
                statement = 'INSERT into authentication (token, slayfy_user_user_id) VALUES(%s, %s)'
                values = (token, id)
                cur.execute('LOCK TABLE authentication IN SHARE MODE')  # não permitir modificações na tabela authentication até terminarmos a transação
                cur.execute(statement, values)

            #se o user já tem um token de autenticação
            else:
                token = cur.fetchone()[0]

            conn.commit()  # commit a transação
            response = {'status': StatusCodes['success'],
                        'results': f'Login feito com sucesso!Token de autenticação: {token}'}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'PUT /slayfy/slayfy_user - error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}

        conn.rollback() #fazer rollback da transação

    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)


#ENDPOINT PARA ADICIONAR UMA MÚSICA
@app.route('/slayfy/song/', methods=['POST'])
def add_song():
    logger.info('POST /slayfy/song/')

    payload = flask.request.get_json()

    conn = db_connection()
    cur = conn.cursor()

    logger.debug(f'PUT /slayfy/song - payload: {payload}')

    token = request.headers.get('Authentication')

    if not token:  # se o user não está autenticado
        response = {'status': StatusCodes['api_error'], 'results': 'There is no user logged in!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    # se o user está autenticado, vamos descodificar o token e obter a informação do user
    secret_key = 'slayfy'
    info = jwt.decode(token, secret_key, algorithms=['HS256'])
    username = info['username']
    id = info['id']
    artist_permit = info['artist_permit']
    admin_permit = info['admin_permit']

    #se o user não é um artista não pode criar músicas
    if not artist_permit:
        response = {'status': StatusCodes['api_error'], 'results': 'Only artists can release songs!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    cur.execute('LOCK TABLE song IN SHARE MODE') #não permitir modificações na tabela song até terminarmos a transação

    # tentar criar música usando a função auxiliar
    response = add_song_helper(conn, cur, payload, id)

    #se ocorreu erro, fazer rollback da transação
    if response[0]['status'] != StatusCodes['success']:
        conn.rollback()

    #senão, commit a transação
    else:
        conn.commit()

    if conn is not None:
        conn.close()

    return flask.jsonify(response[0])


#Função auxiliar para adicionar uma música à base de dados
def add_song_helper(conn, cur, payload, id):
    # verificar que todos os parâmetros existem
    if 'title' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'title not in payload'}
        return (response, -1)

    if 'release_date' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'release_date not in payload'}
        return (response, -1)

    if 'genre' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'genre not in payload'}
        return (response, -1)

    if 'publisher' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'publisher not in payload'}
        return (response, -1)

    if 'other_artists' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'other_artists not in payload'}
        return (response, -1)


    statement = 'INSERT into song(title, release_date, genre, publisher_publisher_id, artist_slayfy_user_user_id) VALUES(%s, %s, %s, %s, %s) RETURNING ismn'
    values = (payload['title'], payload['release_date'], payload['genre'], payload['publisher'], id)

    try:
        cur.execute(statement, values) #inserir a música na base de dados
        ismn = cur.fetchone()[0] #obter o id da música

        #criar associações entre a música e os artistas colaboradores
        for artist_id in payload['other_artists']:
            statement = 'INSERT into artist_song(artist_slayfy_user_user_id, song_ismn) VALUES(%s, %s)'
            values = (artist_id, ismn)
            cur.execute(statement, values)

        response = {'status': StatusCodes['success'], 'results': f'Song released!ID: {ismn}'}
        id = ismn


    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'POST /slayfy/song/ - error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}
        id = -1
        conn.rollback() #se houve erro, fazer rollback da transação

    return (response, id)  # devolvemos a resposta e o ismn da música se houve sucesso, caso contrário -1


#função para inserir um álbum na base de dados
@app.route('/slayfy/album/', methods=['POST'])
def add_album():
    logger.info('POST /slayfy/album/')

    payload = flask.request.get_json()

    conn = db_connection()
    cur = conn.cursor()

    logger.debug(f'PUT /slayfy/album/ - payload: {payload}')

    token = request.headers.get('Authentication') #obter autenticacão

    # se o user não está autenticado
    if not token:
        response = {'status': StatusCodes['api_error'], 'results': 'There is no user logged in!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    #se o user está autenticado, vamos descodificar o token e obter a informação do user
    secret_key = 'slayfy'
    info = jwt.decode(token, secret_key, algorithms=['HS256'])
    username = info['username']
    user_id = info['id']
    artist_permit = info['artist_permit']
    admin_permit = info['admin_permit']

    #se não é um artista, não pode criar um álbum
    if not artist_permit:
        response = {'status': StatusCodes['api_error'], 'results': 'Only artists can release albuns!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    # confirmar que todos os parâmetros necessários existem
    if 'title' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'title not in payload'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    if 'release_date' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'release_date not in payload'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    if 'publisher' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'publisher not in payload'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    if 'songs' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'songs not in payload'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    cur.execute('LOCK TABLE album IN SHARE MODE')  # não permitir modificações na tabela album até terminarmos a transação
    statement = 'INSERT into album(title, release_date, publisher_publisher_id, artist_slayfy_user_user_id) VALUES(%s, %s, %s, %s) RETURNING album_id'
    values = (payload['title'], payload['release_date'], payload['publisher'], user_id)

    try:
        cur.execute(statement, values)  # inserir o álbum
        album_id = cur.fetchone()[0]  # obter id do álbum
        ordem = 1

        for song in payload['songs']:
            #se é necessário criar uma nova música
            if isinstance(song, dict):
                cur.execute('LOCK TABLE song IN SHARE MODE')  # não permitir modificações na tabela album até terminarmos a transação
                response = add_song_helper(conn, cur, song, user_id) #criar a nova música utilizando a função auxiliar

                # se ocorreu um erro na função auxiliar, a transação faz rollback e terminamos a operação toda
                if response[0]['status'] != StatusCodes['success']:
                    conn.rollback()
                    if conn is not None:
                        conn.close()
                    return flask.jsonify(response[0])  # return mensagem de erro

                # se a música foi criada com sucesso, vamos adicioná-la ao álbum na ordem correta
                statement = 'INSERT into songs_in_albuns(association_id, album_order, song_ismn, album_album_id) VALUES (%s, %s, %s, %s)'
                values = (random.randint(0, 2 ** 16 - 1), ordem, response[1], album_id)
                cur.execute(statement, values)
                ordem += 1

            #se a música já foi criada
            else:
                # verificar qual o artista que criou a música
                statement = 'SELECT artist_slayfy_user_user_id FROM song WHERE ismn = %s'
                values = (song,)
                cur.execute(statement, values)

                # se a música não existe, fazemos rollback e terminamos a transação
                if cur.rowcount == 0:
                    conn.rollback()
                    response = {'status': StatusCodes['api_error'], 'results': f'Música {song} não existe'}

                    if conn is not None:
                        conn.close()

                    return flask.jsonify(response)

                # se a música existe
                else:
                    artist = cur.fetchone()[0]

                    #se foi o artista que criou a música, podemos adicioná-la ao álbum
                    if artist == user_id:
                        statement = 'INSERT into songs_in_albuns(association_id, album_order, song_ismn, album_album_id) VALUES (%s, %s, %s, %s)'
                        values = (random.randint(0, 2 ** 16 - 1), ordem, song, album_id)
                        cur.execute(statement, values)
                        ordem += 1

                    #se o artista não criou a música, verificar se colaborou nela
                    else:
                        statement = 'SELECT * from artist_song where artist_slayfy_user_user_id  = %s and song_ismn = %s'
                        values = (user_id, song)

                        cur.execute(statement, values)

                        # se não há colaborações, fazemos rollback e terminamos a operação toda
                        if cur.rowcount == 0:
                            conn.rollback()
                            response = {'status': StatusCodes['api_error'], 'results': f'Artista não colaborou na música {song}'}
                            if conn is not None:
                                conn.close()
                            return flask.jsonify(response)

                        else:
                            # se o artista colaborou na música, então podemos associá-la ao álbum
                            statement = 'INSERT into songs_in_albuns(association_id,album_order, song_ismn, album_album_id) VALUES (%s,%s, %s, %s)'
                            values = (random.randint(0, 2 ** 16 - 1),ordem, song, album_id)
                            cur.execute(statement, values)
                            ordem += 1

        # se foi possível criar e associar todas as músicas, ao álbum, a transação é committed
        conn.commit()  # commit a transação
        response = {'status': StatusCodes['success'], 'results': f'Album released! ID: {album_id}'}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'POST /slayfy/album/ - error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}
        conn.rollback()

    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)


#Função para procurar todas as músicas com uma dada keyword no título
@app.route('/slayfy/song/<keyword>/', methods=['GET'])
def search_song(keyword):
    logger.info('GET /slayfy/song/<keyword>')

    logger.debug(f'keyword: {keyword}')

    conn = db_connection()
    cur = conn.cursor()

    token = request.headers.get('Authentication') #extrair autenticação

    #se o user não está autenticado
    if not token:
        response = {'status': StatusCodes['api_error'], 'results': 'There is no user logged in!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    #qualquer utilizador pode procurar uma música
    try:
        statement = 'SELECT song.title, artist.artistic_name, songs_in_albuns.album_album_id ' \
                    'FROM song ' \
                    'LEFT JOIN artist ON artist.slayfy_user_user_id = song.artist_slayfy_user_user_id ' \
                    'OR artist.slayfy_user_user_id IN (SELECT artist_slayfy_user_user_id FROM artist_song WHERE song_ismn = song.ismn)' \
                    'LEFT JOIN songs_in_albuns on songs_in_albuns.song_ismn = song.ismn ' \
                    'WHERE song.title ILIKE %s'

        values = ('%' + keyword + '%',)
        cur.execute(statement, values) #procurar músicas com essa keyword no título

        # se não houver resultados
        if cur.rowcount == 0:
            response = {'status': StatusCodes['success'], 'results': 'No song found!'}

        else:
            rows = cur.fetchall()
            content = []
            titles = []

            #obter todos os títulos diferentes
            for row in rows:
                if row[0] not in titles:
                    titles.append(row[0])

            #criar um dicionário para cada música
            for title in titles:
                help = {}
                help['1. song title'] = title
                help['2. artists'] = []
                help['3. albuns'] = []
                content.append(help)

            #por a informação no sítio certo
            for row in rows:

                for song_info in content:
                    if song_info['1. song title'] == row[0]:
                        song_info['2. artists'].append(row[1])
                        if row[2] is not None and row[2] not in song_info['3. albuns']:
                            song_info['3. albuns'].append(row[2])
                        break






            response = {'status': StatusCodes['success'], 'results': content}


    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'GET /slayfy/song/<keyword> - error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}

    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)


# __________________________________________________________________________________-

#Função para criar uma playlist
@app.route('/slayfy/playlist', methods=['POST'])
def create_playlist():
    logger.info('POST /slayfy/playlist')
    payload = flask.request.get_json()

    conn = db_connection()
    cur = conn.cursor()
    token = request.headers.get('Authentication') #extrair autenticação

    #se o user não está autenticado
    if not token:
        response = {'status': StatusCodes['api_error'], 'results': 'There is no user logged in!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    # se o user está autenticado, vamos descodificar o token e obter a informação do user
    secret_key = 'slayfy'
    info = jwt.decode(token, secret_key, algorithms=['HS256'])
    username = info['username']
    user_id = info['id']
    artist_permit = info['artist_permit']
    admin_permit = info['admin_permit']

    # só os consumidores podem criar playlists
    if artist_permit or admin_permit:
        response = {'status': StatusCodes['api_error'], 'response': 'Only consumers can create playlists!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    logger.debug(f'POST /slayfy/playlist - payload: {payload}')

    # confirmar a existência de todos os parâmetros (o parâmetro description é opcional)
    if 'title' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'title is required'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    if 'public' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'public is required'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    if 'songs' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'songs are required'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    # verificar se o consumidor é premium ou não
    statement = 'SELECT is_premium from consumer where slayfy_user_user_id = %s'
    values = (user_id,)
    cur.execute(statement, values)

    is_premium = cur.fetchone()[0]

    #se o consumidor não é premium e a playlist a ser criada é privada
    if not is_premium and payload['public'] == 'False':
        response = {'status': StatusCodes['api_error'],
                    'results': 'Only premium consumers can create private playlists!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    #a descrição é opcional
    if 'description' in payload:
        statement = 'INSERT into playlist(title, public, by_system, description, creation_date, consumer_slayfy_user_user_id) VALUES(%s, %s, %s, %s, %s, %s) RETURNING playlist_id'
        values = (payload['title'], payload['public'], False, payload['description'], datetime.datetime.today(), user_id)

    else:
        statement = 'INSERT into playlist(title, public, by_system, creation_date, consumer_slayfy_user_user_id) VALUES(%s, %s, %s, %s, %s) RETURNING playlist_id'
        values = (payload['title'], payload['public'], False, datetime.datetime.today(), user_id)

    try:
        #adicionar a playlist
        cur.execute('LOCK TABLE playlist IN SHARE MODE')  # não permitir modificações na tabela playlist até terminarmos a transação
        cur.execute('LOCK TABLE song_playlist IN SHARE MODE') #não permitir modificações na tabela song_playlist até terminar a transação
        cur.execute(statement, values)
        playlist_id = cur.fetchone()[0]

        # adicionar associações playlist
        for song_id in payload['songs']:
            statement = 'INSERT into song_playlist(song_ismn, playlist_playlist_id) VALUES(%s, %s)'
            values = (song_id, playlist_id)
            cur.execute(statement, values)

        conn.commit()  # commit a transação
        response = {'status': StatusCodes['success'], 'resulsts': 'Playlist created!'}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}

        # fazer rollback da transação
        conn.rollback()

    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)


#Função para procurar informação sobre um artista
@app.route('/slayfy/artist/<artist_id>/', methods=['GET'])
def search_artist(artist_id):
    logger.info('GET /slayfy/artist/<artist_id>')

    logger.debug(f'keyword: {artist_id}')

    conn = db_connection()
    cur = conn.cursor()

    token = request.headers.get('Authentication') #extrair autenticação

    #se o user não está autenticado
    if not token:
        response = {'status': StatusCodes['api_error'], 'results': 'There is no user logged in!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    try:
        #procurar info sobre o artista
        statement = 'SELECT artist.artistic_name, song.ismn, songs_in_albuns.album_album_id, song_playlist.playlist_playlist_id ' \
                    'FROM artist ' \
                    'LEFT JOIN song on song.artist_slayfy_user_user_id = artist.slayfy_user_user_id ' \
                    'OR song.ismn in (SELECT song_ismn from artist_song WHERE artist_song.artist_slayfy_user_user_id = 6) ' \
                    'LEFT JOIN songs_in_albuns on song.ismn = songs_in_albuns.song_ismn ' \
                    'LEFT JOIN song_playlist on song.ismn = song_playlist.song_ismn ' \
                    'where artist.slayfy_user_user_id = %s'

        values = (artist_id,)
        cur.execute(statement, values)

        #se o artista não foi encontrado
        if cur.rowcount == 0:
            response = {'status': StatusCodes['success'], 'results': 'No artist found!'}

        #formatar resposta
        else:
            rows = cur.fetchall()
            songs = []
            albuns = []
            playlists = []
            name = rows[0][0]

            for row in rows:
                if row[1] not in songs:
                    songs.append(row[1])
                if row[2] not in albuns:
                    albuns.append(row[2])
                if row[3] not in playlists:
                    playlists.append(row[3])


            content = {'1. artist name': name, '2. songs': songs, '3. albuns': albuns, '4. playlists': playlists}
            response = {'status': StatusCodes['success'], 'results': content}


    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'GET /slayfy/song/<keyword> - error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}

    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)


#Função para deixar um comentário numa música
@app.route('/slayfy/comment/<song_id>', methods=['POST'])
def leave_comment(song_id):
    logger.info('POST /slayfy/comment/<song_id>')
    logger.debug(f'song id: {song_id}')

    payload = flask.request.get_json()

    conn = db_connection()
    cur = conn.cursor()

    token = request.headers.get('Authentication') #extrair autenticação

    #se o user não está autenticado
    if not token:
        response = {'status': StatusCodes['api_error'], 'results': 'There is no user logged in!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    #se o user está autenticado, vamos descodificar o token e obter a informação do user
    secret_key = 'slayfy'
    info = jwt.decode(token, secret_key, algorithms=['HS256'])
    username = info['username']
    user_id = info['id']
    artist_permit = info['artist_permit']
    admin_permit = info['admin_permit']

    #apenas consumidores podem deixar comentários
    if artist_permit or admin_permit:
        response = {'status': StatusCodes['api_error'], 'response': 'Only consumers can leave comments!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    logger.debug(f'POST /slayfy/comment/<song_id> - payload: {payload}')

    # confirmar a existência de todos os parâmetros
    if 'content' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'content is required in payload'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    # obter o timestamp do comentário
    help = int(time.time())
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(help))

    # a rating é opcional
    if 'rating' in payload:
        statement = 'INSERT into comment(content, rating, comment_time, consumer_slayfy_user_user_id, song_ismn) VALUES (%s, %s, %s, %s, %s) RETURNING comment_id'
        values = (payload['content'], payload['rating'], timestamp, user_id, song_id)

    else:
        statement = 'INSERT into comment(content, comment_time, consumer_slayfy_user_user_id, song_ismn) VALUES (%s, %s, %s, %s) RETURNING comment_id'
        values = (payload['content'], timestamp, user_id, song_id)

    try:
        #adicionar comentário
        cur.execute('LOCK TABLE comment IN SHARE MODE')  # não permitir modificações na tabela comment até terminarmos a transação
        cur.execute(statement, values)
        comment_id = cur.fetchone()[0]

        conn.commit()  #commit a transação
        response = {'status': StatusCodes['success'], 'results': f'Comment created! ID: {comment_id}'}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}

        #fazer rollback da transação
        conn.rollback()

    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)


#Função para deixar uma resposta num comentário pré-existente
@app.route('/slayfy/comment/<song_id>/<parent_comment_id>', methods=['POST'])
def leave_reply(song_id, parent_comment_id):
    logger.info('POST /slayfy/comment/<song_id>/<parent_comment_id>')
    logger.debug(f'song id: {song_id}, parent comment id: {parent_comment_id}')

    payload = flask.request.get_json()

    conn = db_connection()
    cur = conn.cursor()

    token = request.headers.get('Authentication') #extrair autenticação

    #se o user não está autenticado
    if not token:
        response = {'status': StatusCodes['api_error'], 'results': 'There is no user logged in!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    # se o user está autenticado, vamos descodificar o token e obter a informação do user
    secret_key = 'slayfy'
    info = jwt.decode(token, secret_key, algorithms=['HS256'])
    username = info['username']
    user_id = info['id']
    artist_permit = info['artist_permit']
    admin_permit = info['admin_permit']

    #apenas consumidores podem deixar comentários
    if artist_permit or admin_permit:
        response = {'status': StatusCodes['api_error'], 'response': 'Artists cannot leave comments!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    logger.debug(f'POST /slayfy/comment/<song_id> - payload: {payload}')

    # confirmar a existência de todos os parâmetros
    if 'content' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'content is required in payload'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    #obter o timestamp do comentário
    help = int(time.time())
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(help))

    # a rating é opcional
    if 'rating' in payload:
        statement = 'INSERT into comment(content, rating, comment_time, consumer_slayfy_user_user_id, song_ismn) VALUES (%s, %s, %s, %s, %s) RETURNING comment_id'
        values = (payload['content'], payload['rating'], timestamp, user_id, song_id)

    else:
        statement = 'INSERT into comment(content, comment_time, consumer_slayfy_user_user_id, song_ismn) VALUES (%s, %s, %s, %s) RETURNING comment_id'
        values = (payload['content'], timestamp, user_id, song_id)

    try:
        # adicionar comentário à tabela de comentários principais
        cur.execute('LOCK TABLE comment IN SHARE MODE')  # não permitir modificações na tabela comment até terminarmos a transação
        cur.execute(statement, values)

        comment_id = cur.fetchone()[0]  # obter o comment id

        # adicionar associação reply-parent
        statement = 'INSERT into comment_comment(comment_comment_id, comment_comment_id1) VALUES (%s, %s)'
        values = (comment_id, parent_comment_id)
        cur.execute(statement, values)

        conn.commit()  # commit a transação
        response = {'status': StatusCodes['success'], 'results': f'Comment created! ID: {comment_id} '}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}

        # fazer rollback da transação
        conn.rollback()

    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)


#Função para fazer uma subscrição
@app.route('/slayfy/subscription', methods=['POST'])
def make_subscription():
    logger.info('POST /slayfy/subscription')

    payload = flask.request.get_json()

    conn = db_connection()
    cur = conn.cursor()

    token = request.headers.get('Authentication') #extrair autenticação

    #se o user não está autenticado
    if not token:
        response = {'status': StatusCodes['api_error'], 'results': 'There is no user logged in!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    # se o user está autenticado, vamos descodificar o token e obter a informação do user
    secret_key = 'slayfy'
    info = jwt.decode(token, secret_key, algorithms=['HS256'])
    username = info['username']
    user_id = info['id']
    artist_permit = info['artist_permit']
    admin_permit = info['admin_permit']

    #apenas consumidores podem fazer subscrições
    if artist_permit or admin_permit:
        response = {'status': StatusCodes['api_error'], 'response': 'Only consumers can make subscriptions!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    logger.debug(f'POST /slayfy/subscription - payload: {payload}')

    # confirmar a existência de todos os parâmetros
    if 'period' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'period is required in payload'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    if 'cards' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'cards is required in payload'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    try:
        # 1.ver quando vai ser o início da subscrição

        current_timestamp = datetime.datetime.now()

        # ver se o user tem subscrições associadas
        statement = 'SELECT subs_end from subscription where consumer_slayfy_user_user_id = %s'
        values = (user_id,)
        cur.execute(statement, values)

        #se não há subscrições, então o início da nova subscrição é o current time
        if cur.rowcount == 0:
            new_subscription_start = current_timestamp

        #se o user tem subscrições
        else:
            #obter subscrição mais recente
            rows = cur.fetchall()
            last_subscription_end = rows[-1][0]

            # se a última subscrição já expirou, então o início da nova subscrição é o current time
            if last_subscription_end <= current_timestamp:
                new_subscription_start = current_timestamp

            #se a última subscrição ainda está ativa, então a nova subscrição começa após o seu fim
            else:
                new_subscription_start = last_subscription_end

        #2. determinar o final da subscrição
        new_subscription_end = new_subscription_start + relativedelta(months=int(payload['period']))


        # 3. obter o preço da subscrição e o id do plano
        statement = 'SELECT plan_id, price from subscription_plans where duration = %s'
        values = (payload['period'],)
        cur.execute(statement, values)

        # se não existe plano de subscrição com a duração pedida pelo user
        if cur.rowcount == 0:
            response = {'status': StatusCodes['api_error'], 'response': 'Subscription period invalid'}
            conn.rollback() #fazer rollback da transação
            if conn is not None:
                conn.close()
            return flask.jsonify(response)

        rows = cur.fetchone()
        goal_value = rows[1]
        plan_id = rows[0]


        #3. fazer registo da subscrição
        cur.execute('LOCK TABLE subscription IN SHARE MODE') #fazer lock da tabela subscription para evitar conflitos de concorrência
        statement = 'INSERT into subscription(subs_start, subs_end, consumer_slayfy_user_user_id, subscription_plans_plan_id) VALUES (%s, %s, %s, %s)'
        values = (new_subscription_start, new_subscription_end, user_id, plan_id)
        cur.execute(statement, values)


        #4. verificar que todos os cartões que o user quer usar ou lhe pertencem ou não pertencem a ninguém
        for card_id in payload['cards']:

            #verificar se o cartão tem dono
            statement = 'SELECT consumer_slayfy_user_user_id from consumer_card where card_card_id = %s'
            values = (card_id,)
            cur.execute(statement, values)

            # se o cartão ainda não tem um dono, fazer a associação cartão-dono
            if (cur.rowcount == 0):
                statement = 'INSERT into consumer_card(consumer_slayfy_user_user_id, card_card_id) VALUES(%s, %s)'
                values = (user_id, card_id)
                cur.execute(statement, values)

            #se o cartão não tem dono
            else:
                owner_id = cur.fetchone()[0]  # obter o id do dono do cartão

                #se o cartão já tem outro dono, fazer rollback da transação e terminar a operação
                if owner_id != user_id:
                    response = {'status': StatusCodes['api_error'], 'response': 'User cannot use cards that do not belong to him'}
                    conn.rollback()  # fazer rollback da transação
                    if conn is not None:
                        conn.close()
                    return flask.jsonify(response)


        #5.tentar pagar a subscrição utilizando os cartões
        today = datetime.date.today()

        for card_id in payload['cards']:

            #obter balance e expiration date do cartão
            statement = 'SELECT expiration_date, balance from card where card_id = %s'
            values = (card_id,)
            cur.execute(statement, values)
            rows = cur.fetchone()
            expiration_date = rows[0]
            balance = rows[1]


            #se o cartão não está expirado
            if today <= expiration_date:
                # se o valor que queremos pagar for superior ou igual ao do cartão, usamos o total do balance
                if (goal_value >= balance):
                    goal_value = goal_value - balance
                    statement = 'UPDATE card SET balance= %s where card_id = %s'
                    values = (0, card_id)
                    cur.execute(statement, values)


                # se o valor que queremos pagar for inferior ao do cartão, usamos apenas o valor necessário
                else:
                    statement = 'UPDATE card SET balance = %s where card_id = %s'
                    values = (balance - goal_value, card_id)
                    goal_value = 0
                    cur.execute(statement, values)

                #fazer registo da utilização do cartão para pagamento da subscrição
                statement = 'INSERT into subscription_card(subscription_subs_start, subscription_consumer_slayfy_user_user_id, card_card_id) VALUES(%s, %s, %s)'
                values = (new_subscription_start, user_id, card_id)
                cur.execute(statement, values)

            #se foi possível pagar a subscrição
            if goal_value == 0:

                #atualizar o consumidor para premium
                statement = 'UPDATE consumer SET is_premium = %s where slayfy_user_user_id = %s'
                values = ('True', user_id)
                cur.execute(statement, values)

                response = {'status': StatusCodes['success'], 'response': 'Subscription made'}
                conn.commit() #commit a transação
                if conn is not None:
                    conn.close()
                return flask.jsonify(response)

        #se chegou ao fim sem erros mas não conseguiu pagar a subscrição na sua totalidade
        conn.rollback()
        response = {'status': StatusCodes['api_error'], 'response': 'Insufficient funds'}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}

        # fazer rollback da transação
        conn.rollback()

    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

#Função para criar cartões pré-pagos
@app.route('/slayfy/card', methods=['POST'])
def create_prepaid_card():
    logger.info('POST /slayfy/dbproj/card')

    payload = flask.request.get_json()

    conn = db_connection()
    cur = conn.cursor()

    token = request.headers.get('Authentication') #extrair autenticação

    logger.debug(f'POST /slayfy/slayfy/card - payload: {payload}')

    #se o user não está autenticado
    if not token:
        response = {'status': StatusCodes['api_error'], 'results': 'There is no user logged in!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    # se o user está autenticado, vamos descodificar o token e obter a informação do user
    secret_key = 'slayfy'
    info = jwt.decode(token, secret_key, algorithms=['HS256'])
    username = info['username']
    user_id = info['id']
    artist_permit = info['artist_permit']
    admin_permit = info['admin_permit']

    #apenas admins podem criar cartões
    if not admin_permit:
        response = {'status': StatusCodes['api_error'], 'response': 'Must be an admin to create cards!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    #verificar se todos os parâmetros necessários estão na payload
    required_params = ['number_cards', 'original_value']
    missing_params = [param for param in required_params if param not in payload]
    if missing_params:
        response = {'status': StatusCodes['api_error'], 'results': f'Missing parameters: {", ".join(missing_params)}'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)


    card_values = [10, 25, 50]
    card_ids = []

    #se o número de cartões a criar for menor que zero, dá erro
    if int(payload['number_cards']) <= 0:
        response = {'status': StatusCodes['api_error'], 'response': 'Number of cards must be at least 1'}
        if conn is not None:
                conn.close()
        return flask.jsonify(response)

    # verificar que os cartões têm valores válidos
    if int(payload['original_value']) not in card_values:
        response = {'status': StatusCodes['api_error'], 'response': 'Card value must be either 10 or 25 or 50'}
        if conn is not None:
                conn.close()
        return flask.jsonify(response)

    #criar cartões
    else:
        expiration_date = get_expiration_date(30) #cartões apenas são válidos um mês

        for i in range(int(payload['number_cards'])):

            # criar id de cartão válido
            card_id = generate_card_id()
            while is_card_id_taken(card_id):
                card_id = generate_card_id()

            statement = 'INSERT into card(card_id, expiration_date, original_value, balance, admin_slayfy_user_user_id) VALUES  (%s,%s,%s, %s, %s) RETURNING card_id'
            values = (card_id, expiration_date, payload['original_value'], payload['original_value'], user_id)

            try:
                # adicionar cartão
                cur.execute('LOCK TABLE card IN SHARE MODE')  # não permitir modificações na tabela card até terminarmos a transação
                cur.execute(statement, values)
                card_id = cur.fetchone()[0]
                card_ids.append(card_id)

            except (Exception, psycopg2.DatabaseError) as error:
                logger.error(error)
                response = {'status': StatusCodes['internal_error'], 'errors': str(error)}

                #fazer rollback da transação
                conn.rollback()
                if conn is not None:
                    conn.close()
                return flask.jsonify(response)

        #se foi possível criar todos os cartões
        conn.commit()
        response = {'status': StatusCodes['success'], 'results': f'Cards created! ID: {card_ids}'}
        if conn is not None:
                conn.close()
        return flask.jsonify(response)


#função para "ouvir" uma música
@app.route('/slayfy/<keyword>/', methods=['PUT'])
def listen_to_song(keyword):
    logger.info(f'PUT /slayfy/{keyword}')

    conn = db_connection()
    cur = conn.cursor()

    token = request.headers.get('Authentication') #extrair autenticação

    logger.debug('PUT /slayfy/')

    #se o user não está autenticado
    if not token:
        response = {'status': StatusCodes['api_error'], 'results': 'There is no user logged in!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    #se o user está autenticado, vamos descodificar o token e obter a informação do user
    secret_key = 'slayfy'
    info = jwt.decode(token, secret_key, algorithms=['HS256'])

    user_id = info['id']
    admin_permit = info['admin_permit']
    artist_permit = info['artist_permit']

    #apenas consumidores podem ouvir músicas
    if admin_permit or artist_permit:
        response = {'status': StatusCodes['internal_error'], 'results': 'User must be a consumer, not an admin/artist'}
        conn.rollback()  # fazer rollback da transação
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    statement = 'INSERT into listening_history(listening_time, song_ismn,consumer_slayfy_user_user_id) VALUES  (%s, %s,%s)'
    values = (datetime.datetime.today(), keyword, user_id)

    try:
        #inserir registo que a música foi ouvida
        #é preciso lock a tabela song_playlist pois esta operação vai despoletar um trigger que altera a tabela song_playlist
        cur.execute('LOCK TABLE song_playlist IN SHARE MODE')
        cur.execute(statement, values)

        response = {'status': StatusCodes['success'], 'results': f'Song added to listening history. ID: {keyword}'}
        conn.commit()
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    except(Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}
        conn.rollback() #fazer rollback da transação
        if conn is not None:
            conn.close()
        return flask.jsonify(response)


#Função para criar monthly report
@app.route('/slayfy/listening_history/<date>', methods=['GET'])
def create_monthly_report(date):
    logger.info('GET /slayfy/listening_history/{year-month}')

    logger.debug(f'date: {date}')

    conn = db_connection()
    cur = conn.cursor()

    token = request.headers.get('Authentication') # extrair autenticação

    #se o user não está autenticado
    if not token:
        response = {'status': StatusCodes['api_error'], 'results': 'There is no user logged in!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    # se o user está autenticado, vamos descodificar o token e obter a informação do user
    secret_key = 'slayfy'
    info = jwt.decode(token, secret_key, algorithms=['HS256'])
    username = info['username']
    user_id = info['id']
    artist_permit = info['artist_permit']
    admin_permit = info['admin_permit']

    #apenas users podem criar monthly reports
    if  artist_permit or admin_permit:
        response = {'status': StatusCodes['api_error'], 'results': 'Only consumers can get a monthly report!'}
        if conn is not None:
            conn.close()
        return flask.jsonify(response)

    #começamos a ver o relatório começando no dia 20 do mês requerido às 12h
    begin_date = date + '-20 12:00:00'
    timestamp = datetime.datetime.strptime(begin_date, "%Y-%m-%d %H:%M:%S")

    try:
        #construir o monthly report
        statement = "SELECT EXTRACT(MONTH FROM listening_history.listening_time) AS month, " \
                    "song.genre, COUNT(listening_history.song_ismn) AS num_songs_played " \
                    "FROM listening_history " \
                    "JOIN song ON listening_history.song_ismn = song.ismn " \
                    "WHERE listening_history.listening_time <= %s AND listening_history.listening_time >= %s - INTERVAL '12 months' AND listening_history.consumer_slayfy_user_user_id = %s " \
                    "GROUP BY EXTRACT(MONTH FROM listening_history.listening_time), song.genre"

        values = (timestamp, timestamp, user_id)
        cur.execute(statement, values)

        # se não houver resultados
        if cur.rowcount == 0:
            response = {'status': StatusCodes['success'], 'results': 'User has not listened to anything in the past 12 months'}

        #formatar resposta
        else:
            rows = cur.fetchall()
            content = []

            for row in rows:
                if row[0] == 1:
                    month = 'january'
                elif row[0] == 2:
                    month = 'february'
                elif row[0] == 3:
                    month = 'march'
                elif row[0] == 4:
                    month = 'april'
                elif row[0] == 5:
                    month = 'may'
                elif row[0] == 6:
                    month = 'june'
                elif row[0] == 7:
                    month = 'july'
                elif row[0] == 8:
                    month = 'august'
                elif row[0] == 9:
                    month = 'september'
                elif row[0] == 10:
                    month = 'october'
                elif row[0] == 11:
                    month = 'november'
                elif row[0] == 12:
                    month = 'december'

                help = {'1. month': month, '2. genre': row[1], '3. playbacks': row[2]}
                content.append(help)

            response = {'status': StatusCodes['success'], 'results': content}


    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'GET /slayfy/song/<date> - error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}

    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)



##Funções auxiliares

#criar id de cartão único
def generate_card_id():
    min_value = 10 ** 15  # Minimum value with 16 digits
    max_value = (10 ** 16) - 1  # Maximum value with 16 digits
    return random.randint(min_value, max_value)

#ver se o id do cartão está taken
def is_card_id_taken(input_card_id):
    input_card_id = request.json.get('card_id')
    conn = db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM card WHERE card_id = %s", (input_card_id,))
    existing_card = cur.fetchone()
    conn.close()
    if existing_card:
        return True
    else:
        return False

#criar data de expiração
def get_expiration_date(n_days):
    current_date = date.today()
    one_month_later = current_date + timedelta(days=n_days)
    return one_month_later


if __name__ == '__main__':
    # set up logging
    logging.basicConfig(filename='log_file.log')
    logger = logging.getLogger('logger')
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter('%(asctime)s [%(levelname)s]:  %(message)s', '%H:%M:%S')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    host = '127.0.0.1'
    port = 8080

    app.run(host=host, debug=True, threaded=True, port=port)
    logger.info(f'API v1.0 online: http://{host}:{port}')

