"""Assistente interativo de configuração do LLM Usage Widget."""
from __future__ import annotations
import json, os, re, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collector.config import builtin_default_config, default_config_path, load_config


def carregar(path):
    return load_config(path) if path.exists() else builtin_default_config()


def salvar(path, config):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, nome = tempfile.mkstemp(dir=path.parent, prefix='config-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(config, f, ensure_ascii=False, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
        load_config(Path(nome))
        os.replace(nome, path)
    finally:
        if os.path.exists(nome): os.unlink(nome)


def alterar(config, identificador, **opcoes):
    conta = next((p for p in config['providers'] if p['id'] == identificador), None)
    if conta is None: raise ValueError('Conta não encontrada')
    permitidos = {'display_name', 'enabled', 'visible', 'order', 'collection_interval_seconds', 'credentials_path', 'budget'}
    if not set(opcoes) <= permitidos: raise ValueError('Opção desconhecida')
    conta.update(opcoes)


def adicionar(config, identificador, nome, tipo):
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,39}', identificador): raise ValueError('Use letras minúsculas sem acento, números e _; comece com letra.')
    if any(p['id'] == identificador for p in config['providers']): raise ValueError('Já existe uma conta com esse identificador.')
    if not nome.strip() or tipo not in ('quota','metered'): raise ValueError('Nome ou tipo inválido.')
    ordem = max((int(p.get('order', 0)) for p in config['providers']), default=0) + 10
    config['providers'].append({'id':identificador,'display_name':nome.strip(),'kind':tipo,'plugin':'metered_generic' if tipo=='metered' else 'collector.providers.'+identificador+':collect','enabled':False,'visible':True,'order':ordem,'collection_interval_seconds':600,'credential_ref':identificador+'_default'})


def listar(config):
    print('\nContas configuradas:')
    for i, p in enumerate(sorted(config['providers'], key=lambda x: x.get('order',0)), 1):
        print(f"{i}. {p.get('display_name',p['id'])} [{p['id']}] — {'ativa' if p.get('enabled',True) else 'desativada'}, {'visível' if p.get('visible',True) else 'oculta'}; intervalo {p.get('collection_interval_seconds',600)}s; ordem {p.get('order',0)}")


def selecionar(config):
    contas=sorted(config['providers'], key=lambda x:x.get('order',0)); listar(config)
    n=input('Número da conta (Enter cancela): ').strip()
    if not n: return None
    if not n.isdigit() or not 1 <= int(n) <= len(contas): raise ValueError('Número inválido.')
    return contas[int(n)-1]


def modelo_plugin(identificador):
    path=Path(__file__).resolve().parents[1]/'collector'/'providers'/f'{identificador}.py'
    conteudo='''"""Modelo de provedor: implemente a consulta antes de ativar."""\nfrom collector.contract import safe_error\n\ndef collect(cfg, previous):\n    # Implemente uma consulta de uso documentada e somente leitura.\n    # Nunca retorne nem registre credenciais ou resposta bruta.\n    return {"ok": False, "error": safe_error("unsupported", "not_implemented")}\n'''
    with path.open('x',encoding='utf-8',newline='\n') as f: f.write(conteudo)
    return path


def main():
    path=default_config_path()
    try: config=carregar(path)
    except (OSError,ValueError,json.JSONDecodeError) as e:
        print(f'Não foi possível abrir a configuração: {e}'); return 1
    print('Configuração de provedores — LLM Usage Widget')
    print(f'Arquivo: {path}')
    while True:
        print('\n1. Listar contas\n2. Configurar conta\n3. Adicionar conta\n0. Sair')
        escolha=input('Escolha: ').strip()
        try:
            if escolha=='0': return 0
            if escolha=='1': listar(config); continue
            if escolha=='2':
                p=selecionar(config)
                if not p: continue
                print('\n1. Ativar/desativar\n2. Mostrar/ocultar\n3. Intervalo de coleta\n4. Ordem\n5. Nome exibido\n6. Caminho de credencial Claude\n7. Orçamento local (API)\n0. Cancelar')
                a=input('Escolha: ').strip(); v=None
                if a=='1': alterar(config,p['id'],enabled=not p.get('enabled',True))
                elif a=='2': alterar(config,p['id'],visible=not p.get('visible',True))
                elif a in ('3','4'):
                    v=int(input('Segundos (mínimo 60): ' if a=='3' else 'Ordem (número inteiro): '))
                    if (a=='3' and v<60) or (a=='4' and v<0): raise ValueError('Valor fora do intervalo permitido.')
                    alterar(config,p['id'],**{('collection_interval_seconds' if a=='3' else 'order'):v})
                elif a=='5':
                    v=input('Nome exibido: ').strip()
                    if not v: raise ValueError('Nome não pode ficar vazio.')
                    alterar(config,p['id'],display_name=v)
                elif a=='6':
                    if p.get('plugin')!='claude': raise ValueError('Esta opção é para o Claude; cada plugin tem suas próprias opções.')
                    v=input('Caminho do arquivo de credenciais (Enter remove): ').strip()
                    if v: alterar(config,p['id'],credentials_path=v)
                    else: p.pop('credentials_path',None)
                    print('Informe apenas o caminho, nunca o conteúdo ou token.')
                elif a=='7':
                    if p.get('kind') not in ('metered','mixed'): raise ValueError('Orçamento disponível para contas de API monetárias.')
                    from decimal import Decimal, InvalidOperation
                    valor=input('Orçamento (ex.: 20,00; Enter remove): ').strip().replace(',', '.')
                    if not valor: p.pop('budget',None)
                    else:
                        try: numero=Decimal(valor)
                        except InvalidOperation: raise ValueError('Valor inválido.')
                        if not numero.is_finite() or numero <= 0: raise ValueError('O orçamento deve ser positivo.')
                        moeda=input('Moeda ISO (ex.: USD): ').strip().upper()
                        if not re.fullmatch(r'[A-Z]{3}',moeda): raise ValueError('Informe três letras para a moeda.')
                        periodo=input('Identificador do período igual ao do provedor (ex.: 2026-11): ').strip()
                        if not periodo: raise ValueError('O período é obrigatório.')
                        label=input('Nome do período (ex.: Novembro): ').strip() or periodo
                        alterar(config,p['id'],budget={'amount':format(numero,'f'),'currency':moeda,'period':{'id':periodo,'label':label},'source':'local_config'})
                        print('Referência local: o percentual aparece somente se gasto, moeda, período e escopo forem compatíveis.')
                elif a=='0': continue
                else: raise ValueError('Opção inválida.')
                salvar(path,config); print('Configuração salva. A próxima coleta usará as alterações.')
            elif escolha=='3':
                nome=input('Nome que aparecerá na tela: ').strip(); ident=input('Identificador (ex.: deepseek_api): ').strip(); tipo=input('Tipo: 1 = cota em %, 2 = saldo/gasto de API: ').strip()
                if tipo not in ('1','2'): raise ValueError('Escolha 1 ou 2.')
                adicionar(config,ident,nome,'quota' if tipo=='1' else 'metered')
                if tipo=='1':
                    try: print('Modelo de plugin criado em:',modelo_plugin(ident))
                    except FileExistsError: print('Já existe um arquivo de plugin; ele foi preservado.')
                salvar(path,config)
                print('Conta criada DESATIVADA. Ela ainda não coleta dados: é necessário implementar e validar o plugin do serviço.')
                if tipo=='2': print('O plugin monetário genérico é um modelo, ainda sem consulta ao provedor.')
            else: print('Opção inválida.')
        except (ValueError,OSError) as e: print('Não foi possível concluir:', e)

if __name__=='__main__':
    try: raise SystemExit(main())
    except (KeyboardInterrupt,EOFError): print('\nEncerrado.'); raise SystemExit(0)
