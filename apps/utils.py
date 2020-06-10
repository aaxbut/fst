import unicodedata as ud

import Stemmer


def create_search_string(search):
    english = Stemmer.Stemmer('english')
    russian = Stemmer.Stemmer('russian')
    select_stammer = {'en': english, 'ru': russian}
    words = []
    if not search:
        return ''
    rus = []
    eng = []
    for word in search.split():
        for letter in word:
            if 'CYRILLIC' in ud.name(letter):
                rus.append(letter)
            else:
                eng.append(letter)
        if len(rus) > len(eng):
            stemmer = select_stammer.get('ru')
        else:
            stemmer = select_stammer.get('en')
        if stemmer:
            words.append(stemmer.stemWord(word))
    return ' '.join(words) if words else ''
