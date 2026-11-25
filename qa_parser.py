import re
from typing import List, Optional, Iterator
from dataclasses import dataclass

@dataclass
class QAPair:
    question: str
    answer: Optional[str]

class QAParser:
    question_pattern = re.compile(r'^###\s*Frage\s*###\s*:?\s*$', re.IGNORECASE)
    answer_pattern = re.compile(r'^###\s*Antwort\s*###\s*:?\s*$', re.IGNORECASE)
    
    def __init__(self):
        self.qa_pairs: List[QAPair] = []
    
    def parse(self, text: str) -> 'QAParser':
        """
        Parst den Text und extrahiert alle Frage/Antwort-Paare.
        Speichert die Paare in self.qa_pairs.
        
        Args:
            text: Der zu parsende Text
            
        Returns:
            Self für Method Chaining
        """
        lines = text.split('\n')
        self.qa_pairs = []  # Reset bei erneutem Parsen
        current_question = None
        current_content = []
        current_type = None
        
        for i, line in enumerate(lines, 1):
            # Prüfe auf Frage-Marker
            if self.question_pattern.match(line.strip()):
                # Speichere vorheriges Element
                if current_type == 'answer':
                    # Speichere das vollständige Paar
                    answer_content = '\n'.join(current_content).strip()
                    if current_question:
                        self.qa_pairs.append(QAPair(
                            question=current_question,
                            answer=answer_content
                        ))
                elif current_type == 'question':
                    # Frage ohne Antwort
                    content = '\n'.join(current_content).strip()
                    if content:
                        print(f"WARNUNG Zeile {i}: Frage ohne Antwort gefunden")
                        self.qa_pairs.append(QAPair(
                            question=content,
                            answer=None
                        ))
                
                # Starte neue Frage
                current_type = 'question'
                current_content = []
                current_question = None
                continue
            
            # Prüfe auf Antwort-Marker
            if self.answer_pattern.match(line.strip()):
                if current_type == 'question':
                    # Speichere die Frage
                    current_question = '\n'.join(current_content).strip()
                    current_content = []
                elif current_type == 'answer':
                    # Antwort direkt nach Antwort
                    raise ValueError(f"Fehler in Zeile {i}: Auf eine Antwort muss eine Frage folgen!")
                elif current_type is None:
                    # Antwort am Anfang ohne Frage
                    raise ValueError(f"Fehler in Zeile {i}: Antwort ohne vorherige Frage!")
                
                # Starte neue Antwort
                current_type = 'answer'
                continue
            
            # Sammle Content
            if current_type is not None:
                current_content.append(line)
        
        # Verarbeite letztes Element
        if current_type == 'answer':
            # Letztes Element ist eine Antwort - das ist OK
            answer_content = '\n'.join(current_content).strip()
            if current_question:
                self.qa_pairs.append(QAPair(
                    question=current_question,
                    answer=answer_content
                ))
        elif current_type == 'question':
            # Letzte Frage ohne Antwort
            content = '\n'.join(current_content).strip()
            if content:
                print(f"WARNUNG: Letzte Frage ohne Antwort gefunden")
                self.qa_pairs.append(QAPair(
                    question=content,
                    answer=None
                ))
        
        return self
    
    # Erkannte Kopfzeilen bei CSV-Dateien (werden übersprungen)
    csv_header_names = {
        ('question', 'answer'),
        ('frage', 'antwort'),
        ('front', 'back'),
        ('vorderseite', 'rückseite'),
        ('vorderseite', 'rueckseite'),
    }

    def parse_csv(self, text: str, delimiter: str = ',') -> 'QAParser':
        """
        Parst CSV-Text mit zwei Spalten (Frage, Antwort), z. B. Karteikarten-Export.
        Kopfzeile ist optional. Felder in Anführungszeichen dürfen Zeilenumbrüche
        und Trennzeichen enthalten.

        Args:
            text: CSV-Inhalt
            delimiter: Spaltentrenner (Standard: Komma)

        Returns:
            Self für Method Chaining
        """
        import csv
        from io import StringIO

        text = text.lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n')
        self.qa_pairs = []
        reader = csv.reader(StringIO(text, newline=''), delimiter=delimiter)
        first_row = True

        for row in reader:
            if not row or all(not c.strip() for c in row):
                continue  # Leerzeile

            if first_row:
                first_row = False
                if tuple(c.strip().lower() for c in row[:2]) in self.csv_header_names:
                    continue  # Kopfzeile überspringen

            if len(row) > 2:
                raise ValueError(
                    f"Fehler in CSV-Zeile {reader.line_num}: {len(row)} Spalten statt 2 "
                    f"(Komma in einer Zelle ohne Anführungszeichen?)"
                )

            question = row[0].strip()
            answer = row[1].strip() if len(row) == 2 else ''

            if not question:
                raise ValueError(f"Fehler in CSV-Zeile {reader.line_num}: Antwort ohne Frage!")

            if not answer:
                print(f"WARNUNG CSV-Zeile {reader.line_num}: Frage ohne Antwort gefunden")
                self.qa_pairs.append(QAPair(question=question, answer=None))
            else:
                self.qa_pairs.append(QAPair(question=question, answer=answer))

        return self

    def parse_file(self, filename: str, fmt: str = 'auto', delimiter: str = ',') -> 'QAParser':
        """
        Parst eine Datei und extrahiert alle Frage/Antwort-Paare.

        Args:
            filename: Pfad zur zu parsenden Datei
            fmt: 'auto', 'markers' (### Frage ### / ### Antwort ###) oder 'csv'.
                 Bei 'auto': Endung .csv -> CSV, sonst CSV nur, wenn keine
                 Frage-Marker im Text vorkommen.
            delimiter: Spaltentrenner für CSV

        Returns:
            Self für Method Chaining
        """
        with open(filename, 'r', encoding='utf-8-sig') as f:
            text = f.read()

        if fmt == 'auto':
            has_markers = any(self.question_pattern.match(l.strip()) for l in text.split('\n'))
            if filename.lower().endswith('.csv') or not has_markers:
                fmt = 'csv'
            else:
                fmt = 'markers'

        if fmt == 'csv':
            return self.parse_csv(text, delimiter)
        if fmt == 'markers':
            return self.parse(text)
        raise ValueError(f"Unbekanntes Format: {fmt!r} (erlaubt: 'auto', 'markers', 'csv')")

    def __iter__(self) -> Iterator[QAPair]:
        """Ermöglicht Iteration über die QA-Paare"""
        return iter(self.qa_pairs)
    
    def __len__(self) -> int:
        """Gibt die Anzahl der QA-Paare zurück"""
        return len(self.qa_pairs)
    
    def __getitem__(self, index: int) -> QAPair:
        """Ermöglicht Zugriff per Index"""
        return self.qa_pairs[index]
    
    def export_quizlet(self, separator_q: str = '~~Q~~', separator_a: str = '~~A~~') -> str:
        """
        Exportiert die QA-Paare im Quizlet-Format.
        
        Args:
            separator_q: Separator zwischen Frage und Antwort
            separator_a: Separator zwischen Paaren
            
        Returns:
            Formatierter String
        """
        result = ''
        for pair in self.qa_pairs:
            if pair.answer:  # Nur Paare mit Antwort exportieren
                result += (
                    pair.question +
                    separator_q +
                    pair.answer +
                    separator_a
                )
        return result
    
    def export_quizlet_file(self, filename: str, separator_q: str = '~~Q~~', separator_a: str = '~~A~~') -> None:
        """
        Exportiert die QA-Paare in eine Datei im Quizlet-Format.
        
        Args:
            filename: Zieldatei
            separator_q: Separator zwischen Frage und Antwort
            separator_a: Separator zwischen Paaren
        """
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(self.export_quizlet(separator_q, separator_a))
    
    def export_json(self) -> str:
        """Exportiert die QA-Paare als JSON"""
        import json
        data = [
            {
                'question': pair.question,
                'answer': pair.answer
            }
            for pair in self.qa_pairs
        ]
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def export_csv(self, delimiter: str = ',') -> str:
        """Exportiert die QA-Paare als CSV"""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output, delimiter=delimiter)
        writer.writerow(['Question', 'Answer'])
        
        for pair in self.qa_pairs:
            writer.writerow([pair.question, pair.answer or ''])
        
        return output.getvalue()
    
    def get_questions_without_answers(self) -> List[QAPair]:
        """Gibt alle Fragen ohne Antwort zurück"""
        return [pair for pair in self.qa_pairs if pair.answer is None]
    
    def get_statistics(self) -> dict:
        """Gibt Statistiken über die QA-Paare zurück"""
        total = len(self.qa_pairs)
        with_answers = sum(1 for pair in self.qa_pairs if pair.answer is not None)
        without_answers = total - with_answers
        
        return {
            'total_pairs': total,
            'with_answers': with_answers,
            'without_answers': without_answers,
            'completion_rate': (with_answers / total * 100) if total > 0 else 0
        }


# Beispiel-Nutzung
if __name__ == "__main__":
    # Parser erstellen und Datei einlesen
    parser = QAParser()
    
    try:
        parser.parse_file('cards.txt')
        
        # Statistiken anzeigen
        stats = parser.get_statistics()
        print(f"\n=== Statistiken ===")
        print(f"Gefundene Paare: {stats['total_pairs']}")
        print(f"Mit Antwort: {stats['with_answers']}")
        print(f"Ohne Antwort: {stats['without_answers']}")
        print(f"Vollständigkeit: {stats['completion_rate']:.1f}%\n")
        
        # Iteration über alle Paare
        print("=== Alle Paare ===")
        for i, pair in enumerate(parser, 1):
            print(f"--- Paar {i} ---")
            print(f"Frage: {pair.question}")
            print(f"Antwort: {pair.answer if pair.answer else 'KEINE ANTWORT'}")
            print()
        
        # Zugriff per Index
        if len(parser) > 0:
            print(f"=== Erstes Paar ===")
            first = parser[0]
            print(f"Frage: {first.question}")
            print(f"Antwort: {first.answer}\n")
        
        # Fragen ohne Antwort
        incomplete = parser.get_questions_without_answers()
        if incomplete:
            print(f"=== {len(incomplete)} Fragen ohne Antwort ===")
            for pair in incomplete:
                print(f"{pair.question}")
            print()
        
        # Export in verschiedene Formate
        parser.export_quizlet_file('cards.qzl')
        print("✓ Quizlet-Export: cards.qzl")
        
        with open('cards.json', 'w', encoding='utf-8') as f:
            f.write(parser.export_json())
        print("✓ JSON-Export: cards.json")
        
        with open('cards.csv', 'w', encoding='utf-8') as f:
            f.write(parser.export_csv())
        print("✓ CSV-Export: cards.csv")
        
    except ValueError as e:
        print(f"FEHLER: {e}")
    except FileNotFoundError:
        print("FEHLER: Datei 'cards.txt' nicht gefunden!")
