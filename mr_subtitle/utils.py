import base64
import cryptography.fernet
import hashlib
import getpass


table = 'fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF'
tr = dict(map(reversed, enumerate(table)))
s = [11, 10, 3, 8, 4, 6]
xor = 177451812
add = 8728348608


def bv2av(x, prefix=True):
    '''
    Example:
        >>> bv2av('BV1A7411w71V')
        'av90501130'
    '''
    r = sum(tr[x[s[i]]]*58**i for i in range(6))
    id = (r-add) ^ xor
    return f'av{id}' if prefix else str(id)


def av2bv(x):
    '''
    Example:
        >>> av2bv('AV90501130')
        'BV1A7411w71V'
    '''
    x = int(str(x).lower().replace('av', ''))
    x = (x^xor) + add
    r = list('BV1  4 1 7  ')
    for i in range(6):
        r[s[i]] = table[x//58**i%58]
    return ''.join(r)


def md5(string):
    return hashlib.md5(string.encode()).hexdigest()


class Password:
    def __init__(self, *passwords, number=1):
        self._passowrds = passwords or tuple(self.input() for _ in range(number))
        self._number = len(passwords) if passwords else number

    def encrypt(self, content):
        # 加密字符串
        return cryptography.fernet.MultiFernet((
            cryptography.fernet.Fernet(
                base64.urlsafe_b64encode(md5(password).encode())
            ) for password in self._passowrds
        )).encrypt(content.encode()).decode()

    def decrypt(self, token):
        # 解密字符串
        return cryptography.fernet.MultiFernet((
            cryptography.fernet.Fernet(
                base64.urlsafe_b64encode(md5(password).encode())
            ) for password in self._passowrds
        )).decrypt(token.encode()).decode()

    @classmethod
    def input(cls, prompt='Password: ', convert=str):
        return convert(getpass.getpass(prompt=prompt))
