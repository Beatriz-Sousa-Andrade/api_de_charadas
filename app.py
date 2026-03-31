from flask import Flask, jsonify, request
import random
import firebase_admin
from firebase_admin import credentials, firestore
from auth import gerar_token, token_obrigatorio
from flask_cors import CORS 
import os 
from dotenv import load_dotenv 
import json 

load_dotenv() # Carrega as variáveis de ambiente do arquivo .env para o ambiente de execução do phyton. 

# 1. Configuração do Firebase
if os.getenv('VERCEL'):
    #onlien na vercel 
    cred=credentials.Certificate(json.loads(os.getenv('FIREBASE_CREDENTIALS'))) #loads puxa  arquivo, ja o load puxa uma string 
else:
    #localmente
    cred=credentials.Certificate("firebase.json")


firebase_admin.initialize_app(cred)
db = firestore.client()

# 2. Configuração do Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
CORS(app, origins="*")

adm_usuario = os.getenv('ADM_USUARIO')
adm_senha = os.getenv('ADM_SENHA')

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'api': 'charadas',
        'version': '1.0',
        'Author': 'Beatriz',
        'Description': 'API de charadas usando Flask e Firebase'
    }), 200

#========================================================================
#                         ROTA DE LOGIN 
#========================================================================
@app.route("/login", methods=['POST'])
def login():
    dados = request.get_json()

    if not dados:
        return jsonify({"erros": "Envie os dados para login"}), 400
    
    usuario = dados.get("usuario")
    senha = dados.get("senha")

    if not usuario or not senha:
        return jsonify({'error': 'usuario e senha não preenchidos'}), 400
    
    # Agora adm_senha existe e pode ser comparada
    if usuario == adm_usuario and senha == adm_senha:
        token = gerar_token(usuario)
        return jsonify({
            "message": "Login realizado com sucesso!",
            "token": token
        }), 200
    else:
        # CORREÇÃO: Precisa retornar erro se a senha estiver errada
        return jsonify({"error": "Usuário ou senha inválidos"}), 401
    




# Rota 1, método get todas as charadas
@app.route("/charadas", methods=['GET'])
def get_charadas():
    charadas = []
    lista=db.collection('charadas').stream()
    
    for charada in lista:
        charadas.append(charada.to_dict())

    return jsonify(charadas), 200


# Rota 2 método get charadas aleatorias
@app.route("/charadas/aleatoria", methods=['GET'])
def get_charadas_random():
    charadas = []
    lista = db.collection('charadas').stream()
    
    for charada in lista:
        charadas.append(charada.to_dict())

    if not charadas:
        return jsonify({'error': 'Nenhuma charada encontrada no banco.'}), 404

    return jsonify(random.choice(charadas)), 200

# Rota 3 retorna charada pelo id 
@app.route("/charadas/<id>", methods=['GET'])
def get_charada_by_id(id):  
    lista=db.collection('charadas').where('id', '==', id).stream()
    
    for item in lista:
        return jsonify(item.to_dict()), 200
    
    return jsonify({'error': 'Charada não encontrada.'}), 404


#========================================================
#     Rotas privadas 
#========================================================

# Rota 4 método post criar novas charadas
@app.route("/charadas", methods=['POST'])
@token_obrigatorio
def create_charada():
    

    dados = request.get_json()
    if not dados or 'pergunta' not in dados or 'resposta' not in dados:
        return jsonify({'error': 'Dados inválidos.'}), 400
    try:
    #busca pelo computador 
        contador_ref = db.collection('contador').document('controle_id')
        contador_doc = contador_ref.get()
        ultimo_id = contador_doc.to_dict().get('ultimo_id', 0)
        #somar 1 ao ultimo id
        novo_id = ultimo_id + 1
        #atualizar o id do contador no firebase
        contador_ref.update({'ultimo_id': novo_id})


    #cadastrar nova charada 
        db.collection('charadas').add({
            'id': str(novo_id),
            'pergunta': dados['pergunta'],
            'resposta': dados['resposta']      
        })
        return jsonify({'message': 'Charada criada com sucesso.', 'id': str(novo_id)}), 201
    except Exception as e:
            return jsonify({'error': f'Ocorreu um erro ao criar a charada: {str(e)}'}), 500
        
# Rota 5 metodo put alteração total da charada
@app.route("/charadas/<int:id>", methods=['PUT'])
@token_obrigatorio
def charadas_put(id):
    dados = request.get_json()

    if not dados or 'pergunta' not in dados or 'resposta' not in dados:
        return jsonify({'error': 'Dados inválidos.'}), 400
    
    try:
        # Busca o documento com o ID correspondente
        docs = db.collection('charadas').where('id', '==', str(id)).limit(1).get()
        
        # Correção: Verificar se a lista de documentos está vazia
        if len(docs) == 0:
            return jsonify({'error': 'Charada não encontrada.'}), 404

        # Como usamos .limit(1), pegamos o primeiro item
        doc = docs[0]
        doc.reference.update({
            'pergunta': dados['pergunta'],
            'resposta': dados['resposta']
        })
        
        return jsonify({'message': 'Charada atualizada com sucesso.'}), 200
    except Exception as e:
        # Dica: print(e) ajuda a debugar durante o desenvolvimento
        return jsonify({'error': 'Ocorreu um erro ao atualizar a charada.'}), 500
    
#rota 6 método PATCH alteração parcial da charada
@app.route("/charadas/<int:id>", methods=['PATCH'])
@token_obrigatorio
def charadas_patch(id): 
    
    dados = request.get_json()
    if not dados:
        return jsonify({'error': 'Dados inválidos.'}), 400
    
    try:
        # Busca o documento com o ID correspondente
        docs = db.collection('charadas').where('id', '==', str(id)).limit(1).get()
        
        if len(docs) == 0: #o len verifica se a lista de documentos está vazia, ou seja, se a charada existe ou não
            return jsonify({'error': 'Charada não encontrada.'}), 404

        doc = docs[0]
        atualizacoes = {}
        
        if 'pergunta' in dados:
            atualizacoes['pergunta'] = dados['pergunta']
        if 'resposta' in dados:
            atualizacoes['resposta'] = dados['resposta']
        
        if not atualizacoes:
            return jsonify({'error': 'Nenhum campo para atualizar.'}), 400
        
        doc.reference.update(atualizacoes)
        
        return jsonify({'message': 'Charada atualizada com sucesso.'}), 200
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500
    
# Rota 7 método delete excluir charada
@app.route("/charadas/<int:id>", methods=['DELETE'])
@token_obrigatorio
def charadas_delete(id):
    
    try:
        # Busca o documento com o ID correspondente
        docs = db.collection('charadas').where('id', '==', str(id)).limit(1).get()
      #len verifica se a lista de documentos está vazia, ou seja, se a charada existe ou não  
        if len(docs) == 0:
            return jsonify({'error': 'Charada não encontrada.'}), 404
        
        

        doc = docs[0]
        doc.reference.delete()
        
        
        return jsonify({'message': 'Charada excluída com sucesso.'}), 200
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500
    
# trtamnto de erros para rotas não encontradas
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Rota não encontrada.'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erro interno do servidor.'}), 500 


@app.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Não autorizado.'}), 401

if __name__ == '__main__':
    app.run(debug=True)
