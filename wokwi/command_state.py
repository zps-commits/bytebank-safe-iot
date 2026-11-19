"""Contador independente da pilha; reset remoto idempotente para demonstração."""
try:
    import ujson as json
except ImportError:
    import json

class DiagnosticCounter:
    def __init__(self, cache_path='command_ack_cache.json'):
        self.count=0
        self.cache_path=cache_path
        self.acks=[]
        try:
            with open(cache_path) as stream:
                self.acks=json.load(stream)
            if not isinstance(self.acks,list): self.acks=[]
        except (OSError,ValueError):
            self.acks=[]

    def detected(self):
        self.count+=1

    def apply(self, command, device_id):
        if command.get('device_id') != device_id:
            raise ValueError('Comando destinado a outro dispositivo')
        command_id=command.get('command_id')
        if not isinstance(command_id,str) or not command_id:
            raise ValueError('command_id ausente')
        for cached in self.acks:
            if cached['command_id']==command_id:
                return cached['ack']
        if command.get('action')!='reset_counter':
            return {'device_id':device_id,'status':'failed','diagnostic_count':self.count,
                    'message':'Comando nao suportado'}
        ack={'device_id':device_id,'status':'applied','diagnostic_count':0,
             'message':'Contador de diagnostico zerado; pilha preservada'}
        updated=(self.acks+[{'command_id':command_id,'ack':ack}])[-16:]
        # Grava antes de confirmar. Se a escrita falhar, não zera nem envia ACK.
        with open(self.cache_path,'w') as stream:
            json.dump(updated,stream)
        self.acks=updated
        self.count=0
        return ack
