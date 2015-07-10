from openerp import api, fields, models
# from openerp.osv import osv
import xml, commands, string

class positions(models.Model):
    _name = "gpsmaps.positions"
    _pointOnVertex = ""
    
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        if context is None:
            context = {}
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)               
        if user.company_id.id != 1:
            domain += [['device_id.company_id', '=', user.company_id.id]]
        return super(positions, self).read_group(cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        # print "SEARCH positions ------------------------------ "
        if context is None:
            context = {}
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)                
        if user.company_id.id != 1:
            args += [['device_id.company_id', '=', user.company_id.id]]                        
            # print 'FIELDS=',args    
        # self.method(cr, uid)
        return super(positions, self).search(cr, uid, args, offset, limit, order, context=context, count=count)    
    
    """    
    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        print "WRITE positions ------------------------------ "
        #self.method(cr, uid)
        #def method(self,cr, uid):    
        return super(positions, self).write(cr, uid, ids, vals, context=context)  
    """    
    
    def pointInPolygon(self, cr, uid, point, polygon, pointOnVertex=True):        
        _pointOnVertex = pointOnVertex
        point = self.pointStringToCoordinates(cr, uid, point)
        
        vertices = []
        for vertex in polygon:
            vertices.append(self.pointStringToCoordinates(cr, uid, vertex))
        
        intersections = 0
        for i in range(len(vertices)):
        
            vertex1 = vertices[i - 1]
            vertex2 = vertices[i]
            if float(vertex1['y']) == float(vertex2['y']) and float(vertex1['y']) == float(point['y']) and float(point['x']) > min(float(vertex1['x']), float(vertex2['x'])) and float(point['x']) < max(float(vertex1['x']), float(vertex2['x'])): 
                return 'BORDE'

            if float(point['y']) > min(float(vertex1['y']), float(vertex2['y'])) and float(point['y']) <= max(float(vertex1['y']), float(vertex2['y'])) and float(point['x']) <= max(float(vertex1['x']), float(vertex2['x'])) and float(vertex1['y']) != float(vertex2['y']):
                xinters = (float(point['y']) - float(vertex1['y'])) * (float(vertex2['x']) - float(vertex1['x'])) / (float(vertex2['y']) - float(vertex1['y'])) + float(vertex1['x'])
                if xinters == float(point['x']):
                    return 'BORDE'                    
                if float(vertex1['x']) == float(vertex2['x']) or float(point['x']) <= float(xinters):
                    intersections = intersections + 1

        if intersections % 2 != 0: 
            return 'IN'
        return 'OUT'    

    def pointStringToCoordinates(self, cr, uid, point):
        coordinates = string.split(point, ' ')
        coordinate = {}
        coordinate['x'] = coordinates[0]
        coordinate['y'] = coordinates[1]
        return coordinate
        
    def node(self, cr, uid, node, vals, xmldoc):
        if xmldoc.getElementsByTagName(node):
            vals[node] = xmldoc.getElementsByTagName(node)[0].firstChild.data                
            vals['other'] = self.clean_xml(cr, uid, node, vals['other'])
        return vals
        
    def clean_xml(self, cr, uid, string, xml):        
        string_ini = str('<%s>' % (string))
        string_fin = '</%s>' % (string)
        pos_ini = xml.index(string_ini)
        pos_fin = xml.index(string_fin) + len(string_fin)
        
        ini = xml[:pos_ini]
        fin = xml[pos_fin:]
        
        string_end = '%s%s' % (ini, fin)
        # print string,'=',string_end
        return str(string_end)

    def method(self, cr, uid):    
        args_positions = [['times', '=', False]]
        # ids_positions   =super(positions, self).search(cr, 1, args_positions,0,200)
        ids_positions = super(positions, self).search(cr, 1, args_positions, 0, 200)
        # ids_positions   =super(positions, self).search(cr, 1, args_positions,0,1)
        # ids_positions   = super(positions, self).search(cr, 1,[],0,10)
        
        positions_obj = self.pool.get('gpsmaps.positions')
        events_obj = self.pool.get('gpsmaps.events')
        geofence_obj = self.pool.get('gpsmaps.geofence')
        protocol_obj = self.pool.get('gpsmaps.protocol')
        mail_obj = self.pool.get('mail.mail')
        vehicle_obj = self.pool.get('fleet.vehicle')
        
        args_geofence = []
        geofence_ids = geofence_obj.search(cr, uid, args_geofence)                
        
        geofence_datas = geofence_obj.browse(cr, uid, geofence_ids)
        
        if len(geofence_datas) > 0:
            polygons = []            
            for data in geofence_datas:
                # print 'DATA=', data.id , '=', data.geofence
                geofence_id = data.id
                geofence = data.geofence
                points = data.points  
                in_geofence_mail = data.in_geofence_mail
                out_geofence_mail = data.out_geofence_mail
                              
                coordinates = string.split(data.points, ';')                
                polygon = []
                for coordinate in coordinates:
                    polygon.append(coordinate.replace(",", " "))                    
                polygons.append([geofence_id, polygon, in_geofence_mail, out_geofence_mail])    
            

        datas = positions_obj.browse(cr, 1, ids_positions)
        if len(datas) > 0:
            for data in datas:
                vals = {}
                
                datas_vehicle = vehicle_obj.browse(cr, 1, data.device_id.id)

                if data.address:                
                    vals['address'] = data.address
                if data.other:
                    vals['other'] = data.other
                
                for key in vals.keys():                
                    if key == 'other':
                        document = vals['other']
                        xmldoc = xml.dom.minidom.parseString(document)

                        # print commands.getstatusoutput('ls')
                        
                        # doc_root    =xmldoc.documentElement                        
                        # nodeList    =xmldoc.childNodes

                        # nList = nodeList[1].getElementsByTagName("protocol")

                        vals = self.node(cr, uid, 'hdop', vals, xmldoc)
                        vals = self.node(cr, uid, 'milage', vals, xmldoc)
                        vals = self.node(cr, uid, 'state', vals, xmldoc)
                        vals = self.node(cr, uid, 'battery', vals, xmldoc)
                        vals = self.node(cr, uid, 'power', vals, xmldoc)
                        vals = self.node(cr, uid, 'gsm', vals, xmldoc)
                        vals = self.node(cr, uid, 'satellites', vals, xmldoc)
                        # vals=self.node(cr, uid,'protocol',vals,xmldoc)
                        # vals=self.node(cr, uid,'event',vals,xmldoc)                        
                        
                        node = 'milage'                            
                        if xmldoc.getElementsByTagName(node):
                            vals[node] = int(xmldoc.getElementsByTagName(node)[0].firstChild.data) / 1000
                        node = 'protocol'                            
                        if xmldoc.getElementsByTagName(node):
                            # vals=self.node(cr, uid,'hdop',vals,xmldoc)                            
                            vals[node] = xmldoc.getElementsByTagName(node)[0].firstChild.data                
                            vals['other'] = self.clean_xml(cr, uid, node, vals['other'])                                                        
                            args_events = [ ['protocol_id.protocol', '=', vals[node]]  ]

                            if len(events_obj.search(cr, 1, args_events)) > 0:                              
                                vals['event_id'] = events_obj.search(cr, 1, args_events)[0]     
                            
                            
                            # args_protocol         =[ ['name', '=', vals[node]]  ]
                            # protocol_obj.search(cr, 1, args_protocol)[0]
                        node = 'event'
                        if xmldoc.getElementsByTagName(node):
                            # vals=self.node(cr, uid,'hdop',vals,xmldoc)                            
                            vals[node] = xmldoc.getElementsByTagName(node)[0].firstChild.data                
                            vals['other'] = self.clean_xml(cr, uid, node, vals['other'])                                                        
                            args_events = [
                                ['code', '=', vals[node]],
                                ['protocol_id.protocol', '=', vals['protocol']]            
                            ]
                            if len(events_obj.search(cr, 1, args_events)) > 0:                              
                                vals['event_id'] = events_obj.search(cr, 1, args_events)[0]     
                        
                        if len(vals['other']) == 13:
                            vals['other'] = ''

                    if key == 'address':
                        fieldtimes = vals['address']
                        year = fieldtimes[:4]
                        month = fieldtimes[5:7]
                        day = fieldtimes[8:10]
                        hour = fieldtimes[11:13]
                        minute = fieldtimes[14:16]
                        second = fieldtimes[17:19]        
                        vals['times'] = '%s-%s-%s %s:%s:%s' % (year, month, day, hour, minute, second)
                        vals['address'] = ''                    

                        point = '%s %s' % (data.latitude, data.longitude)                                        
                        if len(polygons) > 0:
                            for polygon in polygons:    
                                status_geofence = self.pointInPolygon(cr, uid, point, polygon[1])                    
                                send_email = 0
                                vals_email = {}
                                vals_vehicle = {}                            
                                                                
                                for data_vehicle in datas_vehicle:
                                
                                    # send_email                  =1                                                                  
                                    # vals_email['body_html']     ='Entro a la geocerca %s' %(data_vehicle.geofence_id.name)
                                    model = data_vehicle.model_id.name
                                    plate = data_vehicle.license_plate
                                    driver = data_vehicle.driver_id.name
                                    odometer = data_vehicle.odometer
                                    speed = data.speed
                                    
                                    html_model = ''
                                    if model != False:
                                        html_model = '<tr><td><b>Vehicle</b></td><td> %s </td></tr>' % (model)
                                    html_plate = ''
                                    if plate != False:
                                        html_plate = '<tr><td><b>Plate</b></td><td> %s </td></tr>' % (plate)
                                    html_driver = ''
                                    if driver != False:
                                        html_driver = '<tr><td><b>Driver</b></td><td> %s </td></tr>' % (driver)
                                    html_odometer = ''    
                                    if odometer != False:
                                        html_odometer = '<tr><td><b>Odometer</b></td><td> %s </td></tr>' % (odometer)
                                    html_speed = ''    
                                    if speed != False:
                                        html_speed = '<tr><td><b>Speed</b></td><td> %s </td></tr>' % (speed)
                                    html_geofence = ''
                                    if geofence != False:
                                        html_geofence = '<tr><td><b>Geofence</b></td><td> %s </td></tr>' % (geofence)

                                
                                    html_date = '<tr><td><b>Date</b></td><td> %s </td></tr>' % (vals['times'])
                                    html_geofence = ''

                                    # rute_img      ='http://maps.googleapis.com/maps/api/streetview?size=600x300&location='
                                    # rute_img      ='%s%s,%s' %(rute_img,data.latitude,data.longitude)
                                    
                                    
                                    img_street = '<img border="0" alt="IMAGEN" src="//maps.googleapis.com/maps/api/streetview?size=600x300&location='
                                    img_street = '%s%s,%s">' % (img_street, data.latitude, data.longitude)
                                    
                                    img_map = '<img border="0" alt="IMAGEN" src="//maps.googleapis.com/maps/api/staticmap?zoom=16&size=600x300&maptype=roadmap&markers=color:red%7C'
                                    img_map = '%s%s,%s">' % (img_map, data.latitude, data.longitude)
                                    
                                    html_map = '%s%s' % (img_street, img_map)
                                                                        
                                    vals_email['subject'] = 'SOLLES Alert'
                                        
                                    if status_geofence == 'IN':                            
                                        vals['geofence_id'] = polygon[0]

                                        if data_vehicle.geofence_id.id == False:                                            
                                            vals_vehicle['geofence_id'] = polygon[0]
                                            vehicle_obj.write(cr, uid, data.device_id.id, vals_vehicle, context=None)
                                            if polygon[3]:
                                                send_email = 1                                                                                                                                                      
                                                vals_email['email_to'] = polygon[3]
                                                html_geofence = '<tr><td><b>Event</b></td><td> In geofenece %s</td></tr>' % (data_vehicle.geofence_id.name)                                            
                                                vals_email['subject'] = '%s :: In geofence' % (vals_email['subject'])
                                    
                                    if status_geofence == 'OUT':                                        
                                        if data_vehicle.geofence_id.id == polygon[0]:                                        
                                            vals_vehicle['geofence_id'] = 0                                            
                                            if polygon[3]:
                                                send_email = 1     
                                                vals_email['email_to'] = polygon[3]                                            
                                                html_geofence = '<tr><td><b>Event</b></td><td> Out geofenece %s</td></tr>' % (data_vehicle.geofence_id.name)
                                                vals_email['subject'] = '%s :: Out geofence' % (vals_email['subject'])    
                                            vehicle_obj.write(cr, uid, data.device_id.id, vals_vehicle, context=None)
                                            
                                    vals_email['body_html'] = """<table>%s%s%s%s%s%s%s</table>%s""" % (html_model, html_plate, html_driver, html_date, html_geofence, html_odometer, html_speed, html_map)
                                    
                                    if send_email == 1:                                
                                        vals_email['email_from'] = 'SOLLES Alerta<alertas@soluciones-satelitales.co>m'
                                        if vals_email['email_to']:
                                            # vals_email['email_to']      ='evigra@hotmail.com, evigra@gmail.com, daniel.dazaet@gmail.com, daniel_dazaet@hotmail.com'
                                            # vals_email['email_to']     ='evigra@hotmail.com'
                                            mail_id = mail_obj.create(cr, uid, vals_email, context=None)
                                            mail_obj.send(cr, uid, mail_id)                                
                    positions_obj.write(cr, uid, data.id, vals, context=None)
                    
        return True
        # return vals        
        
    
    address = fields.Char('Calle', size=150)
    altitude = fields.Float('Altura', digits=(6, 2))
    course = fields.Integer('Curso')
    latitude = fields.Float('Latitud', digits=(5, 30))
    longitude = fields.Float('Longitud', digits=(5, 30))
    other = fields.Char('Otros', size=5000)
    state = fields.Char('State', size=10)
    speed = fields.Integer('Velocidad')
    times = fields.Datetime('Fecha')
    valid = fields.Integer('Valido')
    mysql_id = fields.Integer('mysql')
    
    device_id = fields.Many2one('fleet.vehicle', ondelete='set null', string="Vehiculo", index=True)

    protocol = fields.Char('Protocolo', size=15)
    event = fields.Char('Evento', size=40)
    event_id = fields.Many2one('gpsmaps.events', ondelete='set null', string="Eventos", index=True)
    geofence_id = fields.Many2one('gpsmaps.geofence', ondelete='set null', string="Geofence", index=True)
    gsm = fields.Integer('Senal')
    hdop = fields.Float('Exactitud', digits=(2, 2))
    milage = fields.Integer('Millas')
    satellites = fields.Integer('Satelites')
    batery = fields.Float('Bateria', digits=(3, 2))
    battery = fields.Float('Bateria', digits=(3, 2))
    power = fields.Float('Energia', digits=(3, 2))

class geofence(models.Model):
    _name = "gpsmaps.geofence"

    name = fields.Char('Geofence', size=80)
    geofence = fields.Char('Geofence', size=80)
    company_id = fields.Many2one('res.company', ondelete='set null', string="Company", index=True)
    points = fields.Char('Points', size=5000)
    
    in_geofence_mail = fields.Char('In geofence', size=500)
    out_geofence_mail = fields.Char('Out geofence', size=500)


class protocol(models.Model):
    _name = "gpsmaps.protocol"

    protocol = fields.Char('Protocol', size=100)
    name = fields.Char('Nombre', size=100)
    speed = fields.Integer('Velocidad')
    milage = fields.Integer('Millas')

class events(models.Model):
    _name = "gpsmaps.events"


    code = fields.Char('Code', size=10)    
    protocol_id = fields.Many2one('gpsmaps.protocol', ondelete='set null', string="Protocolo", index=True)
    standar_id = fields.Many2one('gpsmaps.standar', ondelete='set null', string="Estandar", index=True)
    name = fields.Char('Name', size=100)

class standar(models.Model):
    _name = "gpsmaps.standar"

    code = fields.Char('Code', size=10)    
    name = fields.Char('Name', size=100)
  
class travel(models.Model):
    _name = "gpsmaps.travel"


    name = fields.Char('Name', size=100)
    code = fields.Char('Code', size=10)
    
    
    start = fields.Char('Start', size=10)
    start_point = fields.Char('Point start', size=10)
    start_geofence_id = fields.Many2one('gpsmaps.geofence', ondelete='set null', string="Geofence Start", index=True)
    
    end = fields.Char('End', size=10)
    end_point = fields.Char('Point end', size=10)
    end_geofence_id = fields.Many2one('gpsmaps.geofence', ondelete='set null', string="Geofence End", index=True)
            
class vehicle(models.Model):
    _inherit = "fleet.vehicle"

    phone = fields.Char('Phone', size=50)
    imei = fields.Char('Imei', size=50)
    position_id = fields.Many2one('gpsmaps.positions', ondelete='set null', string="Ultima Posicion", index=True)
    image_gps = fields.Char('Imagen', size=2)
    geofence_id = fields.Many2one('gpsmaps.geofence', ondelete='set null', string="Geofence", index=True)
    
    all_mail = fields.Integer('Mail general')    
    
    speed_alert = fields.Integer('Velocidad de alerta')
    speed_mail = fields.Integer('Mail por velocidad')
    
    stop_mail = fields.Integer('Mail por parada')
    start_mail = fields.Integer('Mail por inicio')
    
