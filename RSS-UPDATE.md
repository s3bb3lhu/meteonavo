# Nachrichten und Warnungen

Unter Einstellungen → Kanäle & Adressen kann jeder Kanal einen eigenen öffentlichen RSS-/Atom-Link verwenden. Nach Kanal speichern werden die Einstellungen normalerweise innerhalb von etwa 15 Sekunden übernommen. Die grafische Vorschau öffnet in einem neuen Tab; der Ticker wird auch im tatsächlich kodierten Videostream gezeigt.

Der Server fragt Feeds regulär etwa alle fünf Minuten ab, die Ansicht prüft den lokalen Stand minütlich. Unveränderte Schlagzeilen starten das Laufband nicht bei jeder Prüfung neu. Maximal 20 Schlagzeilen mit je 240 Zeichen werden übernommen. Quellenname und eine zusätzliche Uhr werden im ausgestrahlten Ticker nicht eingeblendet; Metadaten und Quelleninformationen bleiben verfügbar.

Zugeordnete aktive amtliche Wetterwarnungen haben Vorrang vor RSS-Schlagzeilen. Eine Warnregion kann in der Verwaltung bestätigt werden. Außerhalb eindeutig zugeordneter Regionen wird keine vermeintlich ortsgenaue Warnung erfunden. Quellenausfälle werden kenntlich gemacht.

Bei Feedfehlern dürfen vorhandene Schlagzeilen höchstens 24 Stunden mit Veraltet-Hinweis weiterlaufen. Ohne verwendbare Daten erscheint ein Fehlerhinweis. Ohne RSS können weiterhin Warnungen beziehungsweise Hinweise zur Warnquelle angezeigt werden.

Es werden nur öffentliche HTTP(S)-Quellen auf Standardports akzeptiert. Interne Netzadressen, eingebettete URL-Zugangsdaten, unsichere Weiterleitungen und übergroße XML-Antworten werden abgewiesen. Nachrichten werden als Text verarbeitet; fremdes HTML wird nicht als ausführbarer Seiteninhalt eingesetzt.

Ein erreichbarer Feed ist keine Erlaubnis zur Weiterverbreitung seiner Inhalte. Betreiber wählen ihre eigene zulässige Quelle; API-Keys oder private Feeds des Projektinhabers sind nicht Bestandteil der Veröffentlichung. Gesamtübersicht: [README.md](README.md).
