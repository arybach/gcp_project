from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

def to_milliseconds(timestamp):
    hours, minutes, seconds = map(int, timestamp.split('.')[0].split(':'))
    milliseconds = int(timestamp.split(' ')[0].split('.')[-1])
    return (hours * 60 * 60 + minutes * 60 + seconds) * 1000 + milliseconds

def from_milliseconds(milliseconds):
    hours = milliseconds // (60 * 60 * 1000)
    milliseconds = milliseconds % (60 * 60 * 1000)
    minutes = milliseconds // (60 * 1000)
    milliseconds = milliseconds % (60 * 1000)
    seconds = milliseconds // 1000
    milliseconds = milliseconds % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    
def cosine_similarity(text1, text2):
    tfidf = TfidfVectorizer().fit_transform([text1, text2])
    return cosine_similarity(tfidf)[0][1]

def aggregate_texts(start_time, end_time, text, next_start_time, next_end_time, next_text):
    similarity = cosine_similarity(text, next_text)
    if similarity > 0.5:
        aggregated_text = text + " " + next_text
        aggregated_start_time = start_time
        aggregated_end_time = next_end_time
        return aggregated_start_time, aggregated_end_time, aggregated_text, True
    else:
        return start_time, end_time, text, False