from .utils import Password


password = Password(number=Password.input('#', int))

oss = dict(
    endpoint=password.decrypt('gAAAAABfA3GXfjC-rOkIzOU4IRH9mF9tfkxExt1GtZTDY3x1CKtGqiemcwsHbKZHImLGuEYlmR6fAieKYB5Fp0mtp3paP9Lgj2wNoWvkCOhjwCV_OESb8wk='),
    bucket_name=password.decrypt('gAAAAABfA3GsWtuQnKC8p517ngnjHt7atcBUw9JVlDfBGeuP4Hth9MlnBHl8ZYm7rnptq1Z81SxKtJ77i6pq-udRaFF9p49RkhHGPCVIJq7vNFSSh0vZ9dk='),
    bucket_domain=password.decrypt('gAAAAABfA3G4zI1MPZhSSKUNCcBz1AQnboBbAlREZjRHLFNC9pDdTpyDReLlrhe9nrwglqjvcCPOE2dVIdyCEKjXYJu5J4cIuFHwX91ed1Psw5XG2GMkE61ljxSsmlRj7CkWRWsVHRSOmG6KKIr2WtRGlOi1yP7XpA=='),
)
clound = dict(
    app_key=password.decrypt('gAAAAABfA3HzaXLZ0V56RJrX2pNDJonN51AXMXpKcUccAvwM5EGkTO54tgWUYeCrBCnV_Yq9X1LR_9953x-XRHZxthEB3bfSZibHuFHphhbi_aUcFnhv5DA='),
)
access_key = dict(
    id=password.decrypt('gAAAAABfA3IFEf-VFQ4aOtfpPewKQtQLbQisyMJ2yhsYJsJw3l9C3Qb3lxAb8zT5TnXBjR05POmVwZN5A4_QRzo0P4nsVRlVEeCGCmFrl4vIgBMAx4R27-k='),
    secret=password.decrypt('gAAAAABfA3IOQo-IgcYYm6je1DT-kNZlnvLyC_To5WpOKyJTqB5281pnkg05oT3Pp7bDomBYl06fLnV6dHqhptvUfU0bawK12pNGn73mVe6kMnfT5JIwSnU='),
)

cache_dir = 'cache'
pickle_path = 'login.pickle'
