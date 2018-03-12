from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy import MetaData, Table
from sqlalchemy import between
from sqlalchemy.sql import func
from sqlalchemy.sql import select
import uuid
import json
import logging
import traceback
import time, sys

class Transformer(object):
	"""Perform the ETL job

	def __init__(self, staging_address, nalanda_address):
		super(Transformer, self).__init__()
		self.staging_engine = create_engine(staging_address)
		staging_metadata = MetaData(bind = self.staging_engine)
		self.Content_Summary_Log = Table('logger_contentsummarylog',staging_metadata,autoload=True,autoload_with=self.staging_engine)
		self.Mastery_Log = Table('logger_masterylog',staging_metadata,autoload=True,autoload_with=self.staging_engine)
		self.Attempt_Log = Table('logger_attemptlog',staging_metadata,autoload=True,autoload_with=self.staging_engine)
		self.Facility_User = Table('kolibriauth_facilityuser',staging_metadata,autoload=True,autoload_with=self.staging_engine)
		self.Collection = Table('kolibriauth_collection',staging_metadata,autoload=True,autoload_with=self.staging_engine)
		self.Membership = Table('kolibriauth_membership',staging_metadata,autoload=True,autoload_with=self.staging_engine)
		self.Content_Node = Table('content_contentnode',staging_metadata,autoload=True,autoload_with=self.staging_engine)
		self.Assessment = Table('content_assessmentmetadata',staging_metadata,autoload=True,autoload_with=self.staging_engine)
		self.staging_session = Session(self.staging_engine)
		Base = automap_base()
		engine = create_engine(nalanda_address)
		Base.prepare(engine,reflect=True)
		self.User_Info_Student = Base.classes.account_userinfostudent
		self.User_Info_Class = Base.classes.account_userinfoclass
		self.User_Info_School = Base.classes.account_userinfoschool
		self.Mastery_Level_Student = Base.classes.account_masterylevelstudent
		self.Mastery_Level_Class = Base.classes.account_masterylevelclass
		self.Mastery_Level_School = Base.classes.account_masterylevelschool
		self.Content = Base.classes.account_content
		self.nalanda_session = Session(engine)"""

	def stagingConn(self, staging_address):
		self.staging_engine = create_engine(staging_address)
		staging_metadata = MetaData(bind = self.staging_engine)
		self.Content_Summary_Log = Table('logger_contentsummarylog',staging_metadata,autoload=True,autoload_with=self.staging_engine)
		self.Mastery_Log = Table('logger_masterylog',staging_metadata,autoload=True,autoload_with=self.staging_engine)
		self.Attempt_Log = Table('logger_attemptlog',staging_metadata,autoload=True,autoload_with=self.staging_engine)
		self.Usersession_Log = Table('logger_usersessionlog',staging_metadata,autoload=True,autoload_with=self.staging_engine)
		self.Facility_User = Table('kolibriauth_facilityuser',staging_metadata,autoload=True,autoload_with=self.staging_engine)
		self.Collection = Table('kolibriauth_collection',staging_metadata,autoload=True,autoload_with=self.staging_engine)
		self.Membership = Table('kolibriauth_membership',staging_metadata,autoload=True,autoload_with=self.staging_engine)
		self.Content_Node = Table('content_contentnode',staging_metadata,autoload=True,autoload_with=self.staging_engine)
		self.Assessment = Table('content_assessmentmetadata',staging_metadata,autoload=True,autoload_with=self.staging_engine)
		self.staging_session = Session(self.staging_engine)
		return self.staging_session

	def nalandaConn(self, nalanda_address):
		Base = automap_base()
		engine = create_engine(nalanda_address)
		Base.prepare(engine,reflect=True)
		self.User_Info_Student = Base.classes.account_userinfostudent
		self.User_Info_Class = Base.classes.account_userinfoclass
		self.User_Info_School = Base.classes.account_userinfoschool
		self.Mastery_Level_Student = Base.classes.account_masterylevelstudent
		self.Mastery_Level_Class = Base.classes.account_masterylevelclass
		self.Mastery_Level_School = Base.classes.account_masterylevelschool
		self.User_Session_Student = Base.classes.usersession_student
		self.User_Session_Class = Base.classes.usersession_class
		self.User_Session_School = Base.classes.usersession_school
		self.Content = Base.classes.account_content
		self.nalanda_session = Session(engine)
		return self.nalanda_session

	def sync_student_info(self, staging_address, nalanda_address):
		try:
			self.staging_session = self.stagingConn(staging_address)
			self.nalanda_session = self.nalandaConn(nalanda_address)

			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of sync_student_info is started at'+ time.strftime("%c"))

			"""totalFacilities = self.staging_session.query(self.Collection.c.dataset_id)\
								.filter(self.Collection.c.kind == 'facility')\
								.order_by(self.Collection.c.dataset_id.asc())\
								.all()
			result = [r[0] for r in totalFacilities]"""
			student_mapping = self.staging_session\
							.query(self.Membership.c.collection_id,self.Facility_User.c.id,self.Facility_User.c.username)\
							.join(self.Facility_User, self.Membership.c.user_id==self.Facility_User.c.id).subquery()
			result_set = self.staging_session\
							.query(student_mapping,self.Collection.c.level,self.Collection.c.parent_id)\
							.join(self.Collection,student_mapping.c.collection_id==self.Collection.c.id).all()
			
			for record in result_set:
				level = record[3]
				if level==1:
					_user_id = record[1]
					user_id = self.uuid2int(_user_id)
					username = record[2]
					_collection_id = record[0]
					collection_id = self.uuid2int(_collection_id)
					old_record = self.nalanda_session.query(self.User_Info_Student)\
									.filter(self.User_Info_Student.student_id==user_id).first()
					if not old_record:
						nalanda_record = self.User_Info_Student(student_id=user_id,student_name=username,parent=collection_id)
						self.nalanda_session.add(nalanda_record)
					else:
						self.nalanda_session.query(self.User_Info_Student)\
									.filter(self.User_Info_Student.student_id==user_id)\
									.update({"parent":collection_id})
			self.nalanda_session.commit()
			self.clear_resource()
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of student information is completed at' + time.strftime("%c"))
		except Exception as e:
			logging.basicConfig(filename='Fetcher.log', level=logging.ERROR)
			logging.error('There is an exception in the Transformer!')
			logging.error(e)
			logging.error(traceback.format_exc())
			raise

	def sync_class_info(self, staging_address, nalanda_address):
		try:
			self.staging_session = self.stagingConn(staging_address)
			self.nalanda_session = self.nalandaConn(nalanda_address)

			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of sync_class_info is started at'+ time.strftime("%c"))		
				
			# totalFacilities = self.staging_session.query(self.Collection.c.dataset_id)\
			# 					.filter(self.Collection.c.kind == 'facility')\
			# 					.order_by(self.Collection.c.dataset_id.asc())\
			# 					.all()
			# result = [r[0] for r in totalFacilities]
			
			student_count = self.staging_session\
								.query(func.count(self.Facility_User.c.id),self.Membership.c.collection_id)\
								.join(self.Membership, self.Membership.c.user_id==self.Facility_User.c.id)\
								.group_by(self.Membership.c.collection_id).subquery()
			result_set = self.staging_session\
							.query(self.Collection.c.id,self.Collection.c.name,self.Collection.c.parent_id,student_count)\
							.filter(self.Collection.c.level==1)\
							.join(student_count, student_count.c.collection_id==self.Collection.c.id).all()
			for record in result_set:
				_class_id = record[0]
				class_id = self.uuid2int(_class_id)
				_school_id = record[2]
				school_id = self.uuid2int(_school_id)
				class_name = record[1]
				total = record[3]
				old_record = self.nalanda_session.query(self.User_Info_Class)\
								.filter(self.User_Info_Class.class_id==class_id).first()
				if not old_record:
					nalanda_record = self.User_Info_Class(class_id=class_id,class_name=class_name,parent=school_id,total_students=total)
					self.nalanda_session.add(nalanda_record)
				else:
					self.nalanda_session.query(self.User_Info_Class)\
								.filter(self.User_Info_Class.class_id==class_id)\
								.update({"total_students":total})
			self.nalanda_session.commit()
			self.clear_resource()
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of class information is completed at' + time.strftime("%c"))
		except Exception as e:
			logging.basicConfig(filename='Fetcher.log', level=logging.ERROR)
			logging.error('There is an exception in the Transformer!')
			logging.error(e)
			logging.error(traceback.format_exc())
			raise

	def sync_school_info(self, staging_address, nalanda_address):
		try:
			self.staging_session = self.stagingConn(staging_address)
			self.nalanda_session = self.nalandaConn(nalanda_address)

			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of sync_school_info is started at'+ time.strftime("%c"))
			# totalFacilities = self.staging_session.query(self.Collection.c.dataset_id)\
			# 					.filter(self.Collection.c.kind == 'facility')\
			# 					.order_by(self.Collection.c.dataset_id.asc())\
			# 					.all()
			# result = [r[0] for r in totalFacilities]
			
			students = self.staging_session\
								.query(self.Facility_User.c.id,self.Facility_User.c.facility_id, self.Membership.c.collection_id)\
								.join(self.Membership, self.Membership.c.user_id==self.Facility_User.c.id).subquery()
			student_filter = self.staging_session\
							.query(students,self.Collection.c.level).join(self.Collection, students.c.collection_id==self.Collection.c.id)\
							.filter(self.Collection.c.level==1).subquery()
			result_set = self.staging_session\
							.query(func.count(student_filter.c.id),student_filter.c.facility_id,self.Collection.c.name)\
							.group_by(student_filter.c.facility_id)\
							.join(self.Collection,self.Collection.c.id==student_filter.c.facility_id).all()
			for record in result_set:
				_school_id = record[1]
				school_id = self.uuid2int(_school_id)
				school_name = record[2]
				total = record[0]
				old_record = self.nalanda_session.query(self.User_Info_School)\
								.filter(self.User_Info_School.school_id==school_id).first()
				if not old_record:
					nalanda_record = self.User_Info_School(school_id=school_id,school_name=school_name,total_students=total)
					self.nalanda_session.add(nalanda_record)
				else:
					self.nalanda_session.query(self.User_Info_School)\
								.filter(self.User_Info_School.school_id==school_id)\
								.update({'total_students':total, 'school_name': school_name})
			self.nalanda_session.commit()
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			self.clear_resource()
			logging.info('The synchronization of school information is completed at' + time.strftime("%c"))
		except Exception as e:
			logging.basicConfig(filename='Fetcher.log', level=logging.ERROR)
			logging.error('There is an exception in the Transformer!')
			logging.error(e)
			logging.error(traceback.format_exc())
			raise

	def sync_content(self, staging_address, nalanda_address):
		try:
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of sync_content is started at'+ time.strftime("%c"))

			self.staging_session = self.stagingConn(staging_address)
			self.nalanda_session = self.nalandaConn(nalanda_address)
			root_set = self.staging_session\
							.query(self.Content_Node.c.id,self.Content_Node.c.title,self.Content_Node.c.kind,self.Content_Node.c.content_id)\
							.filter(self.Content_Node.c.level==0)\
							.all()
			res = {}
			res['topics'] = []
			total = 0
			sub_topics_total = 0
			for root in root_set:
				dic = self.dfs_content_reader(root,root[0], staging_address, nalanda_address)
				res['topics'].append(dic)
				total += dic['total']
				sub_topics_total += dic['counts']
			json_obj = json.dumps(res, ensure_ascii=False)
			old_record = self.nalanda_session.query(self.Content.topic_id)\
							.filter(self.Content.topic_id=='').first()
			if not old_record:
				nalanda_record = self.Content(topic_id='',content_id='',topic_name='',channel_id='',total_questions=total,sub_topics=json_obj,sub_topics_total = sub_topics_total)
				self.nalanda_session.add(nalanda_record)
			else:
				self.nalanda_session.query(self.Content)\
							.filter(self.Content.topic_id=='')\
							.update({'sub_topics':json_obj,'total_questions':total, 'sub_topics_total':sub_topics_total})
			self.nalanda_session.commit()
			self.clear_resource()
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of content information is completed at' + time.strftime("%c"))
		except Exception as e:
			logging.basicConfig(filename='Fetcher.log', level=logging.ERROR)
			logging.error('There is an exception in the Transformer!')
			logging.error(e)
			logging.error(traceback.format_exc())
			raise

	def dfs_content_reader(self, root, channel_id, staging_address, nalanda_address):
		try:
			self.staging_session = self.stagingConn(staging_address)
			self.nalanda_session = self.nalandaConn(nalanda_address)
			count = 0
			if root[2] != 'topic':
				exercise = self.staging_session\
								.query(self.Assessment.c.number_of_assessments)\
								.filter(self.Assessment.c.contentnode_id==root[0]).first()
				res = {}

				if exercise:
					res['counts'] = count + len(exercise) 
					res['total'] = exercise[0]
				else:
					res['total'] = 0
					res['counts'] = 0
				count = res['counts']
				return res
			else:
				sub_level = self.staging_session\
								.query(self.Content_Node.c.id,self.Content_Node.c.title,self.Content_Node.c.kind,self.Content_Node.c.content_id)\
								.filter(self.Content_Node.c.parent_id==root[0]).all()
				res = {}
				res['id'] = root[0]
				res['channelId'] = channel_id
				res['contentId'] = root[3]
				res['name'] = root[1]
				res['children'] = []
				total = 0
				subtopics = 0
				for node in sub_level:
					node_res = self.dfs_content_reader(node,channel_id, staging_address, nalanda_address)
					total += node_res['total']
					subtopics += node_res['counts']
					if 'id' in node_res:
						res['children'].append(node_res)
				res['total'] = total
				res['counts'] = subtopics

				json_obj = json.dumps(res, ensure_ascii=False)
				old_record = self.nalanda_session.query(self.Content).filter(self.Content.topic_id==res['id']).first()
				if not old_record:
					nalanda_record = self.Content(topic_id=res['id'],content_id=res['contentId'],channel_id=res['channelId'],
													topic_name=res['name'],total_questions=res['total'],sub_topics=json_obj, sub_topics_total=subtopics)

					self.nalanda_session.add(nalanda_record)
				else:
					self.nalanda_session.query(self.Content)\
								.filter(self.Content.topic_id==res['id'])\
								.update({'content_id':res['contentId'],'channel_id':res['channelId'],'topic_name':res['name'],\
									'total_questions':res['total'],'sub_topics':json_obj,'sub_topics_total':subtopics})
				self.nalanda_session.commit()
				return res
				logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
				logging.info("complete")
		except Exception as e:
			logging.basicConfig(filename='Fetcher.log', level=logging.ERROR)
			logging.error('There is an exception in the Transformer!')
			logging.error(e)
			logging.error(traceback.format_exc())
			raise

	def completed_questions_aggregation_student(self, start_date, staging_address, nalanda_address):
		try:
			self.staging_session = self.stagingConn(staging_address)
			self.nalanda_session = self.nalandaConn(nalanda_address)
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of completed_questions_aggregation_student is started at'+ time.strftime("%c"))

			# totalFacilities = self.staging_session.query(self.Collection.c.dataset_id)\
			# 					.filter(self.Collection.c.kind == 'facility')\
			# 					.order_by(self.Collection.c.dataset_id.asc())\
			# 					.all()
			# result = [r[0] for r in totalFacilities]

			select_attempt_log = self.staging_session\
								.query(self.Attempt_Log.c.user_id,func.date(self.Attempt_Log.c.completion_timestamp).label("date"),\
									self.Attempt_Log.c.masterylog_id, self.Attempt_Log.c.dataset_id)\
								.filter(self.Attempt_Log.c.completion_timestamp >= start_date).filter(self.Attempt_Log.c.complete == True)\
								.subquery()

			join_mastery_log = self.staging_session.query(select_attempt_log,self.Mastery_Log.c.summarylog_id)\
								.join(self.Mastery_Log, self.Mastery_Log.c.id==select_attempt_log.c.masterylog_id).subquery()

			result_set = self.staging_session.query(join_mastery_log.c.user_id,self.Content_Summary_Log.c.content_id,join_mastery_log.c.date,\
							self.Content_Summary_Log.c.channel_id,func.count(join_mastery_log.c.user_id))\
						.join(self.Content_Summary_Log, self.Content_Summary_Log.c.id==join_mastery_log.c.summarylog_id)\
						.group_by(join_mastery_log.c.date,join_mastery_log.c.user_id,join_mastery_log.c.summarylog_id)\
						.all()
			for record in result_set:
				_student_id = record[0]
				if _student_id:
					student_id = self.uuid2int(_student_id)
				else:
					continue
				content_id = record[1]
				channel_id = record[3]
				date = record[2]
				completed_questions = record[4]
				student_check = self.nalanda_session.query(self.User_Info_Student.student_id)\
									.filter(self.User_Info_Student.student_id==student_id).all()
				if len(student_check)==0:
					continue
				
				topic_ids = self.staging_session.query(self.Content_Node.c.id).filter(self.Content_Node.c.content_id==content_id).all()
				ids = set()
				for topic_id in topic_ids:
					# id for the leaf-level topic
					current_id = topic_id[0]
					while current_id:
						ids.add(current_id)
						parent_id = self.staging_session.query(self.Content_Node.c.parent_id).filter(self.Content_Node.c.id==current_id).first()
						# update the current id with the parent id
						if parent_id:
							current_id = parent_id[0]
						else:
							current_id = None
							logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
							logging.info("Inside else")
				ids.add('')
				for _id in ids:
					try:
						temp = channel_id
						if _id == '':
							channel_id = ''
						# old_record is a tuple
						old_record = self.nalanda_session.query(self.Mastery_Level_Student.completed_questions)\
							.filter(self.Mastery_Level_Student.student_id_id==student_id,self.Mastery_Level_Student.content_id==_id,\
							self.Mastery_Level_Student.channel_id==channel_id,self.Mastery_Level_Student.date==date).first()
						if not old_record:
							logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
							nalanda_record = self.Mastery_Level_Student(id=str(uuid.uuid4()),student_id_id=student_id,content_id=_id,\
													channel_id=channel_id,date=date,completed_questions=completed_questions)
							self.nalanda_session.add(nalanda_record)
						else:
							self.nalanda_session.query(self.Mastery_Level_Student)\
										.filter(self.Mastery_Level_Student.student_id_id==student_id,self.Mastery_Level_Student.content_id==_id,\
											self.Mastery_Level_Student.channel_id==channel_id,self.Mastery_Level_Student.date==date)\
										.update({'completed_questions':old_record[0]+completed_questions})
						channel_id = temp
					except Exception as e:
						logging.basicConfig(filename='Fetcher.log', level=logging.ERROR)
						logging.error('There is an exception in the Transformer!')
						logging.error(e)
						logging.error(traceback.format_exc())
						raise
			self.nalanda_session.commit()
			self.clear_resource()
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of student completed questions is completed at' + time.strftime("%c"))
		except Exception as e:
			logging.basicConfig(filename='Fetcher.log', level=logging.ERROR)
			logging.error('There is an exception in the Transformer!')
			logging.error(e)
			logging.error(traceback.format_exc())
			raise

	def correct_questions_aggregation_student(self, start_date, staging_address, nalanda_address):
		try:
			self.staging_session = self.stagingConn(staging_address)
			self.nalanda_session = self.nalandaConn(nalanda_address)

			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of correct_questions_aggregation_student is started at'+ time.strftime("%c"))

			# totalFacilities = self.staging_session.query(self.Collection.c.dataset_id)\
			# 					.filter(self.Collection.c.kind == 'facility')\
			# 					.order_by(self.Collection.c.dataset_id.asc())\
			# 					.all()
			# result = [r[0] for r in totalFacilities]

			select_attempt_log = self.staging_session\
								.query(self.Attempt_Log.c.user_id,func.date(self.Attempt_Log.c.completion_timestamp).label("date"),\
									self.Attempt_Log.c.masterylog_id)\
								.filter(self.Attempt_Log.c.completion_timestamp >= start_date).filter(self.Attempt_Log.c.correct == 1)\
								.subquery()
			join_mastery_log = self.staging_session.query(select_attempt_log,self.Mastery_Log.c.summarylog_id)\
								.join(self.Mastery_Log, self.Mastery_Log.c.id==select_attempt_log.c.masterylog_id).subquery()
			result_set = self.staging_session.query(join_mastery_log.c.user_id,self.Content_Summary_Log.c.content_id,join_mastery_log.c.date,\
							self.Content_Summary_Log.c.channel_id,func.count(join_mastery_log.c.user_id))\
						.join(self.Content_Summary_Log, self.Content_Summary_Log.c.id==join_mastery_log.c.summarylog_id)\
						.group_by(join_mastery_log.c.date,join_mastery_log.c.user_id,join_mastery_log.c.summarylog_id)\
						.all()
			for record in result_set:
				_student_id = record[0]
				student_id = self.uuid2int(_student_id)
				content_id = record[1]
				channel_id = record[3]
				date = record[2]
				correct_questions = record[4]
				student_check = self.nalanda_session.query(self.User_Info_Student.student_id)\
									.filter(self.User_Info_Student.student_id==student_id).all()
				if len(student_check)==0:
					continue
				topic_ids = self.staging_session.query(self.Content_Node.c.id).filter(self.Content_Node.c.content_id==content_id).all()
				ids = set()
				for topic_id in topic_ids:
					# id for the leaf-level topic
					current_id = topic_id[0]
					while current_id:
						ids.add(current_id)
						parent_id = self.staging_session.query(self.Content_Node.c.parent_id).filter(self.Content_Node.c.id==current_id).first()
						# update the current id with the parent id
						if parent_id:
							current_id = parent_id[0]
						else:
							current_id = None
				ids.add('')
				for id in ids:
					temp = channel_id
					if id == '':
						channel_id = ''
					old_record = self.nalanda_session.query(self.Mastery_Level_Student.correct_questions)\
						.filter(self.Mastery_Level_Student.student_id_id==student_id,self.Mastery_Level_Student.content_id==id,\
						self.Mastery_Level_Student.channel_id==channel_id,self.Mastery_Level_Student.date==date).first()
					if not old_record:
						nalanda_record = self.Mastery_Level_Student(id=str(uuid.uuid4()),student_id_id=student_id,content_id=id,\
												channel_id=channel_id,date=date,correct_questions=correct_questions)
						self.nalanda_session.add(nalanda_record)
					else:
						self.nalanda_session.query(self.Mastery_Level_Student)\
									.filter(self.Mastery_Level_Student.student_id_id==student_id,self.Mastery_Level_Student.content_id==id,\
										self.Mastery_Level_Student.channel_id==channel_id,self.Mastery_Level_Student.date==date)\
									.update({'correct_questions':old_record[0]+correct_questions})
					channel_id = temp
			self.nalanda_session.commit()
			self.clear_resource()
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of student correct questions is completed at' + time.strftime("%c"))
		except Exception as e:
			logging.basicConfig(filename='Fetcher.log', level=logging.ERROR)
			logging.error('There is an exception in the Transformer!')
			logging.error(e)
			logging.error(traceback.format_exc())
			raise

	def attempted_questions_aggregation_student(self, start_date, staging_address, nalanda_address):
		try:
			self.staging_session = self.stagingConn(staging_address)
			self.nalanda_session = self.nalandaConn(nalanda_address)

			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of attempted_questions_aggregation_student is started at'+ time.strftime("%c"))

			# totalFacilities = self.staging_session.query(self.Collection.c.dataset_id)\
			# 					.filter(self.Collection.c.kind == 'facility')\
			# 					.order_by(self.Collection.c.dataset_id.asc())\
			# 					.all()
			# result = [r[0] for r in totalFacilities]
			
			select_attempt_log = self.staging_session\
								.query(self.Attempt_Log.c.user_id,func.date(self.Attempt_Log.c.start_timestamp).label("date"),\
									self.Attempt_Log.c.masterylog_id)\
								.filter(self.Attempt_Log.c.start_timestamp >= start_date)\
								.subquery()

			join_mastery_log = self.staging_session.query(select_attempt_log,self.Mastery_Log.c.summarylog_id)\
								.join(self.Mastery_Log, self.Mastery_Log.c.id==select_attempt_log.c.masterylog_id).subquery()

			result_set = self.staging_session.query(join_mastery_log.c.user_id,self.Content_Summary_Log.c.content_id,join_mastery_log.c.date,\
							self.Content_Summary_Log.c.channel_id,func.count(join_mastery_log.c.user_id))\
						.join(self.Content_Summary_Log, self.Content_Summary_Log.c.id==join_mastery_log.c.summarylog_id)\
						.group_by(join_mastery_log.c.date,join_mastery_log.c.user_id,join_mastery_log.c.summarylog_id)\
						.all()

			for record in result_set:
				_student_id = record[0]
				if _student_id is not None:
					student_id = self.uuid2int(_student_id)
				content_id = record[1]
				channel_id = record[3]
				date = record[2]
				attempt_questions = record[4]
				student_check = self.nalanda_session.query(self.User_Info_Student.student_id)\
									.filter(self.User_Info_Student.student_id==student_id).all()
				if len(student_check)==0:
					continue
				topic_ids = self.staging_session.query(self.Content_Node.c.id).filter(self.Content_Node.c.content_id==content_id).all()
				ids = set()
				for topic_id in topic_ids:
					# id for the leaf-level topic
					current_id = topic_id[0]
					while current_id:
						ids.add(current_id)
						parent_id = self.staging_session.query(self.Content_Node.c.parent_id).filter(self.Content_Node.c.id==current_id).first()
						# update the current id with the parent id
						if parent_id:
							current_id = parent_id[0]
						else:
							current_id = None

				ids.add('')
				for id in ids:
					temp = channel_id
					if id == '':
						channel_id = ''
					old_record = self.nalanda_session.query(self.Mastery_Level_Student.attempt_questions)\
						.filter(self.Mastery_Level_Student.student_id_id==student_id,self.Mastery_Level_Student.content_id==id,\
						self.Mastery_Level_Student.channel_id==channel_id,self.Mastery_Level_Student.date==date).first()
					if not old_record:
						nalanda_record = self.Mastery_Level_Student(id=str(uuid.uuid4()),student_id_id=student_id,content_id=id,\
												channel_id=channel_id,date=date,attempt_questions=attempt_questions)
						self.nalanda_session.add(nalanda_record)
					else:
						self.nalanda_session.query(self.Mastery_Level_Student)\
									.filter(self.Mastery_Level_Student.student_id_id==student_id,self.Mastery_Level_Student.content_id==id,\
										self.Mastery_Level_Student.channel_id==channel_id,self.Mastery_Level_Student.date==date)\
									.update({'attempt_questions':old_record[0]+attempt_questions})
					channel_id = temp
			self.nalanda_session.commit()
			self.clear_resource()
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of student attempted questions is completed at' + time.strftime("%c"))
		except Exception as e:
			logging.basicConfig(filename='Fetcher.log', level=logging.ERROR)
			logging.error('There is an exception in the Transformer!')
			logging.error(e)
			logging.error(traceback.format_exc())
			raise

	def exercise_mastered_by_student(self, start_date, staging_address, nalanda_address):
		try:
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of student mastered questions is started at'+ time.strftime("%c"))

			self.staging_session = self.stagingConn(staging_address)
			self.nalanda_session = self.nalandaConn(nalanda_address)
			query = "SET sql_mode = '';"
			sindbConnection = self.staging_session.connection()
			sindbConnection.execute(query)
			selectMasteryLog = self.staging_session\
							.query(self.Mastery_Log.c.user_id,func.date(self.Mastery_Log.c.completion_timestamp).label("date"),\
							self.Mastery_Log.c.id, self.Mastery_Log.c.summarylog_id)\
							.filter(self.Mastery_Log.c.completion_timestamp >= start_date).filter(self.Mastery_Log.c.complete == 1)\
							.subquery()

			result_set = self.staging_session.query(selectMasteryLog.c.user_id,self.Content_Summary_Log.c.content_id,selectMasteryLog.c.date,\
						self.Content_Summary_Log.c.channel_id,func.count(selectMasteryLog.c.user_id))\
						.join(self.Content_Summary_Log, self.Content_Summary_Log.c.id==selectMasteryLog.c.summarylog_id)\
						.group_by(selectMasteryLog.c.user_id, self.Content_Summary_Log.c.content_id, self.Content_Summary_Log.c.id)\
						.all()
			for record in result_set:
				_student_id = record[0]
				student_id = self.uuid2int(_student_id)
				content_id = record[1]
				channel_id = record[3]
				date = record[2]
				mastered_topics = record[4]
				student_check = self.nalanda_session.query(self.User_Info_Student.student_id)\
										.filter(self.User_Info_Student.student_id==student_id).all()
				if len(student_check)==0:
					continue

				topic_ids = self.staging_session.query(self.Content_Node.c.id).filter(self.Content_Node.c.content_id==content_id).all()
				ids = set()
				for topic_id in topic_ids:
					# id for the leaf-level topic
					current_id = topic_id[0]
					while current_id:
						ids.add(current_id)
						parent_id = self.staging_session.query(self.Content_Node.c.parent_id).filter(self.Content_Node.c.id==current_id).first()
						# update the current id with the parent id
						if parent_id:
							current_id = parent_id[0]
						else:
							current_id = None
				ids.add('')
				for id in ids:
					temp = channel_id
					if id == '':
						channel_id = ''
					old_record = self.nalanda_session.query(self.Mastery_Level_Student.mastered)\
						.filter(self.Mastery_Level_Student.student_id_id==student_id,self.Mastery_Level_Student.content_id==id,\
						self.Mastery_Level_Student.channel_id==channel_id,self.Mastery_Level_Student.date==date).first()
					if not old_record:
						nalanda_record = self.Mastery_Level_Student(id=str(uuid.uuid4()),student_id_id=student_id,content_id=id,\
												channel_id=channel_id,date=date,mastered=mastered_topics)
						self.nalanda_session.add(nalanda_record)
					else:
						self.nalanda_session.query(self.Mastery_Level_Student)\
									.filter(self.Mastery_Level_Student.student_id_id==student_id,self.Mastery_Level_Student.content_id==id,\
										self.Mastery_Level_Student.channel_id==channel_id,self.Mastery_Level_Student.date==date)\
									.update({'mastered':old_record[0]+mastered_topics})
					channel_id = temp
			self.nalanda_session.commit()
			self.clear_resource()
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of student mastered questions is completed at' + time.strftime("%c"))
		except Exception as e:
			logging.basicConfig(filename='Fetcher.log', level=logging.ERROR)
			logging.error('There is an exception in the Transformer!')
			logging.error(e)
			logging.error(traceback.format_exc())
			raise

	def exercise_attempts_by_students(self, start_date, staging_address, nalanda_address):
		try:
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of exercise attempts by student is started at'+ time.strftime("%c"))

			result_set = self.staging_session.query(self.Content_Summary_Log.c.user_id, self.Content_Summary_Log.c.content_id,func.date(self.Content_Summary_Log.c.end_timestamp).label("date"),\
									self.Content_Summary_Log.c.channel_id, func.count(self.Content_Summary_Log.c.user_id))\
									.filter(between(self.Content_Summary_Log.c.progress,'0.25','1.0')).filter(self.Content_Summary_Log.c.kind == 'exercise')\
									.filter(self.Content_Summary_Log.c.start_timestamp >= start_date)\
									.group_by(self.Content_Summary_Log.c.id,self.Content_Summary_Log.c.user_id, self.Content_Summary_Log.c.end_timestamp)\
									.all()

			for record in result_set:
				_student_id = record[0]
				student_id = self.uuid2int(_student_id)
				content_id = record[1]
				channel_id = record[3]
				date = record[2]
				topic_attempts = record[4]
				student_check = self.nalanda_session.query(self.User_Info_Student.student_id)\
										.filter(self.User_Info_Student.student_id==student_id).all()

				if len(student_check)==0:
					continue

				topic_ids = self.staging_session.query(self.Content_Node.c.id).filter(self.Content_Node.c.content_id==content_id).all()
				ids = set()
				for topic_id in topic_ids:
					# id for the leaf-level topic
					current_id = topic_id[0]
					while current_id:
						ids.add(current_id)
						parent_id = self.staging_session.query(self.Content_Node.c.parent_id).filter(self.Content_Node.c.id==current_id).first()
						# update the current id with the parent id
						if parent_id:
							current_id = parent_id[0]
						else:
							current_id = None
				ids.add('')
				for id in ids:
					temp = channel_id
					if id == '':
						channel_id = ''
					old_record = self.nalanda_session.query(self.Mastery_Level_Student.attempt_exercise)\
						.filter(self.Mastery_Level_Student.student_id_id==student_id,self.Mastery_Level_Student.content_id==id,\
						self.Mastery_Level_Student.channel_id==channel_id,self.Mastery_Level_Student.date==date).first()
					if not old_record:
						nalanda_record = self.Mastery_Level_Student(id=str(uuid.uuid4()),student_id_id=student_id,content_id=id,\
												channel_id=channel_id,date=date, attempt_exercise=topic_attempts)
						self.nalanda_session.add(nalanda_record)
					else:
						self.nalanda_session.query(self.Mastery_Level_Student)\
									.filter(self.Mastery_Level_Student.student_id_id==student_id,self.Mastery_Level_Student.content_id==id,\
										self.Mastery_Level_Student.channel_id==channel_id,self.Mastery_Level_Student.date==date)\
									.update({'attempt_exercise':old_record[0]+topic_attempts})
					channel_id = temp
			self.nalanda_session.commit()
			self.clear_resource()
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of exercise attempts by student is completed at' + time.strftime("%c"))
		except Exception as e:
			logging.basicConfig(filename='Fetcher.log', level=logging.ERROR)
			logging.error('There is an exception in the Transformer!')
			logging.error(e)
			logging.error(traceback.format_exc())
			raise 

	def user_session_student(self, start_date, staging_address, nalanda_address):
		try:
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of student user session is started at'+ time.strftime("%c"))
			self.staging_session = self.stagingConn(staging_address)
			self.nalanda_session = self.nalandaConn(nalanda_address)

			result_set = self.staging_session\
						.query(self.Usersession_Log.c.user_id, func.date(self.Usersession_Log.c.last_interaction_timestamp).label("date"), self.Usersession_Log.c.start_timestamp, self.Usersession_Log.c.last_interaction_timestamp)\
						.order_by(self.Usersession_Log.c.id.asc())\
						.filter(self.Usersession_Log.c.last_interaction_timestamp >=start_date)\
						.all()

			for record in result_set:
				_student_id = record[0]
				student_id = self.uuid2int(_student_id)
				date = record[1]
				total_usage = (record[3] - record[2]).seconds

				student_check = self.nalanda_session.query(self.User_Info_Student.student_id)\
								.filter(self.User_Info_Student.student_id==student_id).all()
				if len(student_check)==0:
					continue

				old_record = self.nalanda_session.query(self.User_Session_Student)\
							.filter(self.User_Session_Student.student_id_id==student_id,self.User_Session_Student.date==date)\
							.first()

				if not old_record:
					nalanda_record = self.User_Session_Student(student_id_id=student_id,total_usage=total_usage,\
												date=date)
					self.nalanda_session.add(nalanda_record)
				else:
					self.nalanda_session.query(self.User_Session_Student)\
								.filter(self.User_Session_Student.student_id_id==student_id,\
								self.User_Session_Student.date==date)\
								.update({'total_usage':old_record.total_usage + total_usage})
			self.nalanda_session.commit()
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of user_session status is completed at' + time.strftime("%c"))
		except Exception as e:
			logging.basicConfig(filename='Fetcher.log', level=logging.ERROR)
			logging.error('There is an exception in the Transformer!')
			logging.error(e)
			logging.error(traceback.format_exc())
			raise 
		
	# def completed_student(self, start_date):
	# 	try:
	# 		result_set = self.staging_session\
	# 					.query(self.Content_Summary_Log.c.user_id,self.Content_Summary_Log.c.content_id,\
	# 						func.date(self.Content_Summary_Log.c.completion_timestamp),self.Content_Summary_Log.c.channel_id) \
	# 					.filter(self.Content_Summary_Log.c.completion_timestamp >= start_date)
	# 		for record in result_set:
	# 			_student_id = record[0]
	# 			student_id = self.uuid2int(_student_id)
	# 			content_id = record[1]
	# 			channel_id = record[3]
	# 			date = record[2]
	# 			student_check = self.nalanda_session.query(self.User_Info_Student.student_id)\
	# 								.filter(self.User_Info_Student.student_id==student_id).all()
	# 			if len(student_check)==0:
	# 				continue
	# 			old_record = self.nalanda_session.query(self.Mastery_Level_Student).filter(self.Mastery_Level_Student.student_id_id==student_id\
	# 				,self.Mastery_Level_Student.content_id==content_id,self.Mastery_Level_Student.channel_id==channel_id,self.Mastery_Level_Student.date==date)\
	# 				.first()
	# 			if not old_record:
	# 				nalanda_record = self.Mastery_Level_Student(id=str(uuid.uuid4()),student_id_id=student_id,content_id=content_id,\
	# 										channel_id=channel_id,date=date,completed=True)
	# 				self.nalanda_session.add(nalanda_record)
	# 			else:
	# 				self.nalanda_session.query(self.Mastery_Level_Student)\
	# 							.filter(self.Mastery_Level_Student.student_id_id==student_id,self.Mastery_Level_Student.content_id==content_id,\
	# 								self.Mastery_Level_Student.channel_id==channel_id,self.Mastery_Level_Student.date==date)\
	# 							.update({'completed':True})
	# 		self.nalanda_session.commit()
	# 		logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
	# 		logging.info('The synchronization of topic completion status is completed at' + time.strftime("%c"))
	# 	except Exception as e:
	# 		logging.basicConfig(filename='Fetcher.log', level=logging.ERROR)
	# 		logging.error('There is an exception in the Transformer!')
	# 		logging.error(e)
	# 		logging.error(traceback.format_exc())
	# 		raise

	def user_session_aggregation_class(self, start_date, staging_address, nalanda_address):
		try:
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of user session class aggregation is started at'+ time.strftime("%c"))
			self.staging_session = self.stagingConn(staging_address)
			self.nalanda_session = self.nalandaConn(nalanda_address)
			result_set = self.nalanda_session\
							.query(self.User_Session_Student.date, func.sum(self.User_Session_Student.total_usage),self.User_Info_Student.parent)\
							.filter(self.User_Session_Student.date >= start_date)\
							.join(self.User_Info_Student,self.User_Session_Student.student_id_id==self.User_Info_Student.student_id)\
							.group_by(self.User_Session_Student.date, self.User_Info_Student.parent).all()
			
			for record in result_set:
				date = record[0]
				total_usage = record[1]
				class_id = record[2]
				old_record = self.nalanda_session.query(self.User_Session_Class)\
							.filter(self.User_Session_Class.class_id_id==class_id,self.User_Session_Class.date==date).first()
				if not old_record:
					nalanda_record = self.User_Session_Class(class_id_id=class_id,total_usage=total_usage,\
										date=date)
					self.nalanda_session.add(nalanda_record)
				else:
					self.nalanda_session.query(self.User_Session_Class)\
									.filter(self.User_Session_Class.class_id_id==class_id,self.User_Session_Class.date==date)\
									.update({'total_usage':total_usage})
			self.nalanda_session.commit()
			self.clear_resource()
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of user session class progress data is completed at' + time.strftime("%c"))
		except Exception as e:
			logging.basicConfig(filename='Fetcher.log', level=logging.ERROR)
			logging.error('There is an exception in the Transformer!')
			logging.error(e)
			logging.error(traceback.format_exc())
			raise

	def mastery_level_aggregation_class(self, start_date, staging_address, nalanda_address):
		try:
			self.staging_session = self.stagingConn(staging_address)
			self.nalanda_session = self.nalandaConn(nalanda_address)
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of mastery_level_aggregation_class is started at'+ time.strftime("%c"))
			result_set = self.nalanda_session\
							.query(self.Mastery_Level_Student.date,self.Mastery_Level_Student.content_id,self.Mastery_Level_Student.channel_id,\
							func.sum(self.Mastery_Level_Student.completed_questions),func.sum(self.Mastery_Level_Student.correct_questions),\
							func.sum(self.Mastery_Level_Student.attempt_questions),func.sum(self.Mastery_Level_Student.mastered),\
							func.sum(self.Mastery_Level_Student.attempt_exercise), self.User_Info_Student.parent)\
							.filter(self.Mastery_Level_Student.date >= start_date)\
							.join(self.User_Info_Student,self.Mastery_Level_Student.student_id_id==self.User_Info_Student.student_id)\
							.group_by(self.Mastery_Level_Student.date,self.Mastery_Level_Student.content_id,self.Mastery_Level_Student.channel_id,
							self.User_Info_Student.parent).all()
			for record in result_set:
				date = record[0]
				content_id = record[1]
				channel_id = record[2]
				completed_questions = record[3]
				correct_questions = record[4]
				attempt_questions = record[5]
				mastered = record[6]
				attempt_exercise = record[7]
				class_id = record[8]
				old_record = self.nalanda_session.query(self.Mastery_Level_Class)\
								.filter(self.Mastery_Level_Class.class_id_id==class_id,self.Mastery_Level_Class.content_id==content_id,\
									self.Mastery_Level_Class.channel_id==channel_id,self.Mastery_Level_Class.date==date).first()
				if not old_record:
					nalanda_record = self.Mastery_Level_Class(id=str(uuid.uuid4()),class_id_id=class_id,content_id=content_id,\
										channel_id=channel_id,date=date,completed_questions=completed_questions,correct_questions=correct_questions,\
										attempt_questions=attempt_questions,mastered=mastered, attempt_exercise=attempt_exercise)
					self.nalanda_session.add(nalanda_record)
				else:
					self.nalanda_session.query(self.Mastery_Level_Class)\
									.filter(self.Mastery_Level_Class.class_id_id==class_id,self.Mastery_Level_Class.content_id==content_id,\
									self.Mastery_Level_Class.channel_id==channel_id,self.Mastery_Level_Class.date==date)\
									.update({'completed_questions':completed_questions,'correct_questions':correct_questions,\
										'attempt_questions':attempt_questions,'mastered':mastered,'attempt_exercise':attempt_exercise})
			self.nalanda_session.commit()
			self.clear_resource()
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of class progress data is completed at' + time.strftime("%c"))
		except Exception as e:
			logging.basicConfig(filename='Fetcher.log', level=logging.ERROR)
			logging.error('There is an exception in the Transformer!')
			logging.error(e)
			logging.error(traceback.format_exc())
			raise

	def user_session_aggregation_school(self, start_date, staging_address, nalanda_address):
		try:
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of user session school aggregation is started at'+ time.strftime("%c"))
			self.staging_session = self.stagingConn(staging_address)
			self.nalanda_session = self.nalandaConn(nalanda_address)

			result_set = self.nalanda_session\
							.query(self.User_Session_Class.date, self.User_Session_Class.total_usage, self.User_Info_Class.parent)\
							.filter(self.User_Session_Class.date >= start_date)\
							.join(self.User_Info_Class,self.User_Session_Class.class_id_id==self.User_Info_Class.class_id)\
							.group_by(self.User_Session_Class.date, self.User_Session_Class.id, self.User_Info_Class.parent).all()

			for record in result_set:
				date = record[0]
				total_usage = record[1]
				school_id = record[2]
				old_record = self.nalanda_session.query(self.User_Session_School)\
								.filter(self.User_Session_School.school_id_id==school_id,\
								self.User_Session_School.date==date).first()
				if not old_record:
					nalanda_record = self.User_Session_School(school_id_id=school_id, total_usage=total_usage, date=date)
					self.nalanda_session.add(nalanda_record)
				else:
					self.nalanda_session.query(self.User_Session_School)\
									.filter(self.User_Session_School.school_id_id==school_id, self.User_Session_School.date==date)\
									.update({'total_usage':old_record.total_usage + total_usage})
			self.nalanda_session.commit()
			self.clear_resource()
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of user session school progress data is completed at' + time.strftime("%c"))
		except Exception as e:
			logging.basicConfig(filename='Fetcher.log', level=logging.ERROR)
			logging.error('There is an exception in the Transformer!')
			logging.error(e)
			logging.error(traceback.format_exc())
			raise

	def mastery_level_aggregation_school(self, start_date, staging_address, nalanda_address):
		try:
			self.staging_session = self.stagingConn(staging_address)
			self.nalanda_session = self.nalandaConn(nalanda_address)
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of mastery_level_aggregation_school is started at'+ time.strftime("%c"))
			result_set = self.nalanda_session\
							.query(self.Mastery_Level_Class.date,self.Mastery_Level_Class.content_id,self.Mastery_Level_Class.channel_id,\
								func.sum(self.Mastery_Level_Class.completed_questions),func.sum(self.Mastery_Level_Class.correct_questions),\
								func.sum(self.Mastery_Level_Class.attempt_questions),func.sum(self.Mastery_Level_Class.mastered),func.sum(self.Mastery_Level_Class.attempt_exercise),\
								self.User_Info_Class.parent)\
							.filter(self.Mastery_Level_Class.date >= start_date)\
							.join(self.User_Info_Class,self.Mastery_Level_Class.class_id_id==self.User_Info_Class.class_id)\
							.group_by(self.Mastery_Level_Class.date,self.Mastery_Level_Class.content_id,self.Mastery_Level_Class.channel_id,
							self.User_Info_Class.parent).all()
			for record in result_set:
				date = record[0]
				content_id = record[1]
				channel_id = record[2]
				completed_questions = record[3]
				correct_questions = record[4]
				attempt_questions = record[5]
				mastered = record[6]
				attempt_exercise = record[7]
				school_id = record[8]
				old_record = self.nalanda_session.query(self.Mastery_Level_School)\
								.filter(self.Mastery_Level_School.school_id_id==school_id,self.Mastery_Level_School.content_id==content_id,\
									self.Mastery_Level_School.channel_id==channel_id,self.Mastery_Level_School.date==date).first()
				if not old_record:
					nalanda_record = self.Mastery_Level_School(id=str(uuid.uuid4()),school_id_id=school_id,content_id=content_id,\
										channel_id=channel_id,date=date,completed_questions=completed_questions,correct_questions=correct_questions,\
										attempt_questions=attempt_questions,mastered=mastered, attempt_exercise=attempt_exercise)
					self.nalanda_session.add(nalanda_record)
				else:
					self.nalanda_session.query(self.Mastery_Level_School)\
									.filter(self.Mastery_Level_School.school_id_id==school_id,self.Mastery_Level_School.content_id==content_id,\
									self.Mastery_Level_School.channel_id==channel_id,self.Mastery_Level_School.date==date)\
									.update({'completed_questions':completed_questions,'correct_questions':correct_questions,\
										'attempt_questions':attempt_questions,'mastered':mastered,'attempt_exercise':attempt_exercise})
			self.nalanda_session.commit()
			self.clear_resource()
			logging.basicConfig(filename='Fetcher.log', level=logging.INFO)
			logging.info('The synchronization of school progress data is completed at' + time.strftime("%c"))
		except Exception as e:
			logging.basicConfig(filename='Fetcher.log', level=logging.ERROR)
			logging.error('There is an exception in the Transformer!')
			logging.error(e)
			logging.error(traceback.format_exc())
			raise

	def clear_log(self, start_date, staging_address, nalanda_address):
		try:
			self.staging_session = self.stagingConn(staging_address)
			self.nalanda_session = self.nalandaConn(nalanda_address)
			self.nalanda_session.query(self.Mastery_Level_Student).filter(self.Mastery_Level_Student.date>=start_date).delete()
			self.nalanda_session.query(self.Mastery_Level_Class).filter(self.Mastery_Level_Class.date>=start_date).delete()
			self.nalanda_session.query(self.Mastery_Level_School).filter(self.Mastery_Level_School.date>=start_date).delete()
		except Exception as e:
			logging.basicConfig(filename='Transformer.log', level=logging.ERROR)
			logging.error('There is an exception in the Transformer!')
			logging.error(e)
			logging.error(traceback.format_exc())
			raise

	def clear_resource(self):
		self.nalanda_session.close()
		self.staging_session.close()

	def uuid2int(self, raw):
		return uuid.UUID(raw).int >> 65