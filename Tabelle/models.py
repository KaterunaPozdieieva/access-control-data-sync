
from django.db import models


class TGast(models.Model):
    ext_oid = models.IntegerField()
    ext_id = models.IntegerField()
    employeenumber = models.CharField(db_column='employeeNumber', max_length=50, db_collation='Latin1_General_CI_AS', blank=True, null=True)  # Field name made lowercase.
    sn = models.CharField(max_length=50, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    givenname = models.CharField(db_column='givenName', max_length=50, db_collation='Latin1_General_CI_AS', blank=True, null=True)  # Field name made lowercase.
    title = models.CharField(max_length=50, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    title_berichtigt = models.CharField(max_length=50, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    kategorie = models.CharField(max_length=255, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    schrank_nr_alt = models.CharField(max_length=255, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    schrank_nr_neu = models.CharField(max_length=255, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    schrank = models.CharField(max_length=255, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    funktion = models.CharField(max_length=1024, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    funktion_kurz = models.CharField(max_length=1024, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    adt = models.CharField(db_column='ADT', max_length=10, db_collation='Latin1_General_CI_AS', blank=True, null=True)  # Field name made lowercase.
    einrichtung_lang = models.CharField(max_length=1024, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    einrichtung = models.CharField(max_length=512, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    bild = models.CharField(max_length=1, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    anrede = models.CharField(max_length=255, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    layout = models.CharField(max_length=255, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    gedruckt_am = models.DateTimeField(blank=True, null=True)
    kartennummer = models.IntegerField(blank=True, null=True)
    barcode = models.IntegerField(blank=True, null=True)
    createtime = models.DateTimeField(blank=True, null=True)
    modifytime = models.DateTimeField(blank=True, null=True)
    mifareid_dez = models.CharField(max_length=40, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    benutzergruppe = models.CharField(max_length=60, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    berechtigungsgruppe = models.CharField(max_length=60, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    gelesen_am = models.DateTimeField(blank=True, null=True)
    abteilung = models.CharField(max_length=128, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    active = models.BooleanField(blank=True, null=True)
    verlorene_karte = models.BooleanField(blank=True, null=True)
    individualpermissions = models.CharField(db_column='individualPermissions', max_length=500, db_collation='Latin1_General_CI_AS', blank=True, null=True)  # Field name made lowercase.
    mifareid_paxton = models.CharField(max_length=10, db_collation='Latin1_General_CI_AS')

    #button in admin panel 'web seite aufmachen.
    def get_absolute_url(self):
        return reverse('post', kwargs={'post_id': self.pk})

    class Meta:
        managed = False
        db_table = 't_Gast'
        ordering = ['createtime', 'kartennummer']
        verbose_name = 'Gäste_Tabelle'
        verbose_name_plural = 'Gäste_Tabelle'



class TStudenten(models.Model):
    ext_oid = models.IntegerField()
    ext_id = models.IntegerField()
    employeenumber = models.CharField(db_column='employeeNumber', max_length=50, db_collation='Latin1_General_CI_AS', blank=True, null=True)  # Field name made lowercase.
    sn = models.CharField(max_length=50, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    givenname = models.CharField(db_column='givenName', max_length=50, db_collation='Latin1_General_CI_AS', blank=True, null=True)  # Field name made lowercase.
    title = models.CharField(max_length=50, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    title_berichtigt = models.CharField(max_length=50, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    kategorie = models.CharField(max_length=255, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    schrank_nr_neu = models.CharField(max_length=255, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    schrank = models.CharField(max_length=255, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    funktion = models.CharField(max_length=1024, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    funktion_kurz = models.CharField(max_length=1024, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    adt = models.CharField(db_column='ADT', max_length=10, db_collation='Latin1_General_CI_AS', blank=True, null=True)  # Field name made lowercase.
    einrichtung_lang = models.CharField(max_length=1024, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    einrichtung = models.CharField(max_length=512, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    bild = models.CharField(max_length=1, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    anrede = models.CharField(max_length=255, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    layout = models.CharField(max_length=255, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    gedruckt_am = models.DateTimeField(blank=True, null=True)
    kartennummer = models.IntegerField(blank=True, null=True)
    barcode = models.IntegerField(blank=True, null=True)
    createtime = models.DateTimeField(blank=True, null=True)
    modifytime = models.DateTimeField(blank=True, null=True)
    mifareid_dez = models.CharField(max_length=40, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    benutzergruppe = models.CharField(max_length=60, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    berechtigungsgruppe = models.CharField(max_length=60, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    gelesen_am = models.DateTimeField(blank=True, null=True)
    abteilung = models.CharField(max_length=128, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    kst = models.CharField(max_length=12, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    unterabteilung = models.CharField(max_length=192, db_collation='Latin1_General_CI_AS', blank=True, null=True)
    active = models.BooleanField(blank=True, null=True)
    verlorene_karte = models.BooleanField(blank=True, null=True)
    individualpermissions = models.CharField(db_column='individualPermissions', max_length=500, db_collation='Latin1_General_CI_AS', blank=True, null=True)  # Field name made lowercase.
    mifareid_paxton = models.CharField(max_length=10, db_collation='Latin1_General_CI_AS')


        #button in admin panel 'web seite aufmachen.
    def get_absolute_url(self):
        return reverse('post', kwargs={'post_id': self.pk})
    class Meta:
        managed = False
        db_table = 't_studenten'
        ordering = ['createtime', 'kartennummer']
        verbose_name = 'Studenten_Tabelle'
        verbose_name_plural = 'Studenten_Tabelle'
        






class PaxtonViewWeb(models.Model):
    row_id = models.BigIntegerField(primary_key=True)
    employeenumber = models.CharField(db_column='employeeNumber', max_length=50, blank=True, null=True)  # Field name made lowercase.
    berechtigungsgruppe = models.IntegerField(blank=True, null=True)
    individualpermissions = models.CharField(db_column='individualPermissions', max_length=4000, blank=True, null=True)  # Field name made lowercase.
    benutzergruppe = models.IntegerField(blank=True, null=True)
    kartennummer = models.IntegerField(blank=True, null=True)
    createtime = models.DateTimeField(blank=True, null=True)
    mifareid_paxton = models.CharField(max_length=10)
    givenname = models.CharField(db_column='givenName', max_length=50, blank=True, null=True)  # Field name made lowercase.
    sn = models.CharField(max_length=50, blank=True, null=True)
    austritt = models.DateTimeField(db_column='Austritt', blank=True, null=True)  # Field name made lowercase.
    endofcontract = models.DateTimeField(db_column='EndOfContract', blank=True, null=True)  # Field name made lowercase.
    oelong = models.CharField(db_column='OElong', max_length=50, blank=True, null=True)  # Field name made lowercase.
    mstbroe = models.CharField(db_column='MSTBROE', max_length=50, blank=True, null=True)  # Field name made lowercase.
    dvh_text = models.CharField(db_column='DVH_TEXT', max_length=255, blank=True, null=True)  # Field name made lowercase.
    schrank = models.IntegerField(blank=True, null=True)
    karte_active = models.BooleanField(blank=True, null=True)
    verlorene_karte = models.BooleanField(blank=True, null=True)


        #button in admin panel 'web seite aufmachen.
    def get_absolute_url(self):
        return reverse('post', kwargs={'post_id': self.pk})





    class Meta:
        managed = False
        db_table = 'paxton_view_web'
        ordering = ['createtime', 'kartennummer']
        verbose_name = 'Mitarbeiten_Tabelle'
        verbose_name_plural = 'Mitarbeiten_Tabelle'

